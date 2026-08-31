"""
Smoke test: run every normalization method and every imputation approach on
synthetic data to verify that all dependencies are correctly installed.

Exit code 0  -- all methods pass or raise the expected NotImplementedError.
Exit code 1  -- at least one unexpected failure.
"""
from __future__ import annotations

import sys
import time
import traceback
import warnings

import importlib.metadata

import numpy as np
import pandas as pd
import rpy2
import rpy2.robjects as ro

from bench_shared import (
    BATCH_COL,
    BIO_COL,
    METHODS,
    prepare_dataset,
    prepare_dataset_imputed,
)

# ── Environment info ──────────────────────────────────────────────────────────
print("=" * 60)
print("ENVIRONMENT")
print("=" * 60)
print(f"  Python   : {sys.version.split()[0]}")
try:
    rpy2_ver = rpy2.__version__
except AttributeError:
    rpy2_ver = importlib.metadata.version("rpy2")
print(f"  rpy2     : {rpy2_ver}")
try:
    r_ver = str(ro.r("R.version$version.string")[0])
    print(f"  R        : {r_ver}")
except Exception as exc:
    print(f"  R version: UNKNOWN ({exc})")

_CRITICAL_PKGS = [
    "FSQN", "qsmooth", "missForest", "softImpute",
    "limma", "sva", "RUVSeq", "batchelor", "edgeR", "DESeq2",
    "HarmonizR", "TDM",
    "DWDLargeR", "huge", "DBNorm", "AMDBNorm",
    "DASC", "exploBATCH", "ruv", "NOISeq", "bapred", "Harman",
]
print("  R packages:")
for pkg in _CRITICAL_PKGS:
    try:
        ro.r(f"library({pkg})")
        print(f"    {pkg:<20} OK")
    except Exception:
        print(f"    {pkg:<20} MISSING")

RNG     = np.random.default_rng(42)
N_SAMP  = 80
N_GENES = 200
N_BATCH = 3
N_DIAG  = 2

batches    = [f"BatchGPL{i}"  for i in range(N_BATCH)]
diags      = [f"Diag{i}"      for i in range(N_DIAG)]
sample_ids = [f"S{i:04d}"     for i in range(N_SAMP)]

batch_labels = [batches[i % N_BATCH] for i in range(N_SAMP)]
diag_labels  = [diags[i % N_DIAG]   for i in range(N_SAMP)]

exp = pd.DataFrame(
    # +2 offset ensures no zeros after np.round().clip(0) inside normalize_vst
    RNG.exponential(5, size=(N_SAMP, N_GENES)).astype(float) + 2.0,
    index=sample_ids,
    columns=[f"GENE{j:04d}" for j in range(N_GENES)],
)

ann = pd.DataFrame(
    {
        BATCH_COL:                         batch_labels,
        BIO_COL:                           diag_labels,
        "Diagnosis_cell_type_general":     diag_labels,
        "COHORT_LABEL":                    batch_labels,
        "coo_bg":                          ["GCB"] * N_SAMP,
    },
    index=sample_ids,
)


def _is_rpy2_conversion_error(exc: Exception) -> bool:
    """True if the exception is an rpy2 type-conversion failure, not an intentional skip."""
    msg = str(exc)
    return any(kw in msg for kw in ("Conversion", "py2rpy", "rpy2py", "converter"))


# ── Imputation ────────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("IMPUTATION METHODS")
print("=" * 60)

imp_results: dict[str, dict] = {}

t0 = time.time()
try:
    e, _ = prepare_dataset(ann, exp)
    assert e.shape[0] > 0
    imp_results["strict"] = {"status": "PASS", "elapsed": time.time() - t0}
except Exception:
    imp_results["strict"] = {"status": "FAIL", "elapsed": time.time() - t0, "tb": traceback.format_exc()}

exp_with_na = exp.copy()
mask = RNG.random(exp_with_na.shape) < 0.10
exp_with_na[mask] = np.nan

for imp in ("knn", "missforest", "softimpute"):
    t0 = time.time()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            e, _ = prepare_dataset_imputed(ann, exp_with_na, method=imp)
        assert e.isna().sum().sum() == 0, "NAs remain after imputation"
        imp_results[imp] = {"status": "PASS", "elapsed": time.time() - t0}
    except NotImplementedError as exc:
        status = "FAIL" if _is_rpy2_conversion_error(exc) else "SKIP"
        imp_results[imp] = {"status": status, "elapsed": time.time() - t0, "tb": traceback.format_exc()}
    except Exception:
        imp_results[imp] = {"status": "FAIL", "elapsed": time.time() - t0, "tb": traceback.format_exc()}

for name, r in imp_results.items():
    print(f"  {name:<20} {r['status']}  ({r['elapsed']:.1f}s)")


# ── Normalization ─────────────────────────────────────────────────────────────
print()
print("=" * 60)
print("NORMALIZATION METHODS")
print("=" * 60)

norm_results: dict[str, dict] = {}
e_strict, a_strict = prepare_dataset(ann, exp)

for key, (fn, harshness) in METHODS.items():
    t0 = time.time()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = fn(e_strict, a_strict, batch_col=BATCH_COL, bio_col=BIO_COL)
        assert isinstance(out, pd.DataFrame), "output is not a DataFrame"
        assert out.shape[0] > 0, "output has 0 rows"
        norm_results[key] = {"status": "PASS", "elapsed": time.time() - t0}
    except NotImplementedError as exc:
        status = "FAIL" if _is_rpy2_conversion_error(exc) else "SKIP"
        norm_results[key] = {
            "status": status,
            "elapsed": time.time() - t0,
            "tb": traceback.format_exc(),
            "msg": str(exc),
        }
    except Exception:
        norm_results[key] = {"status": "FAIL", "elapsed": time.time() - t0, "tb": traceback.format_exc()}

for name, r in sorted(norm_results.items()):
    status = r["status"]
    elapsed = r.get("elapsed", 0)
    msg = r.get("msg", "")
    if status == "SKIP":
        print(f"  {name:<30} {status}  ({elapsed:.1f}s)  {msg[:60]}")
    else:
        print(f"  {name:<30} {status}  ({elapsed:.1f}s)")


# ── Failure report ────────────────────────────────────────────────────────────
failed_norm = {k: v for k, v in norm_results.items() if v["status"] == "FAIL"}
failed_imp  = {k: v for k, v in imp_results.items()  if v["status"] == "FAIL"}
any_fail    = bool(failed_norm or failed_imp)

if any_fail:
    print()
    print("=" * 60)
    print("FAILURE DETAILS")
    print("=" * 60)
    for name, r in {**failed_imp, **failed_norm}.items():
        print(f"\n{'─' * 60}")
        print(f"FAILED: {name}")
        print("─" * 60)
        print(r.get("tb", "(no traceback)"))
    failed_names = sorted(failed_imp) + sorted(failed_norm)
    print(f"\nRESULT: {len(failed_names)} FAILURE(S): {', '.join(failed_names)}")
    sys.exit(1)

# Also print tracebacks for SKIPs so they're visible for debugging
skipped = {k: v for k, v in {**imp_results, **norm_results}.items()
           if v["status"] == "SKIP" and "tb" in v}
if skipped:
    print()
    print("=" * 60)
    print("SKIP DETAILS (intentional NotImplementedError)")
    print("=" * 60)
    for name, r in skipped.items():
        print(f"\n  {name}: {r.get('msg', '')}")

print()
print("RESULT: All methods PASS or SKIP (expected). Dependencies OK.")
sys.exit(0)
