"""
revision_lib.py — shared helpers of the Article 1 revision (NARGAB-2026-312).

Plan: article_1_revision_implementation_plan_261029.md (sections in brackets below).

This module is the ONLY place where the revision touches the frozen benchmark code
(plan §4): it imports functions from `harmonization-scripts/bench_shared.py` and
`harmonization-metrics-calculation/compute_batch_metrics.py` and wraps them; it never
copies or edits them. Everything that needs R (rpy2) is imported lazily inside the
function that uses it, so the pure-Python parts (designs, folds, panel rule, four
scores, ledger) run on JupyterHub, where R has no Bioconductor packages.

Contents
--------
- paths, S3 layout of the revision (`revision_261029/…`)
- `PUBLICATION_NAMES`, `METHOD_DISPLAY_NAMES`, `STRATEGY_DISPLAY_NAMES` ("code · name"),
  `STRATEGY_CODES`, `STRATEGY_PLAIN_NAMES` (plan §1.1)
- confounding statistics: bias-corrected Cramér's V, AMI
- gradient designs: n_b, n_{b,g}(λ) with largest-remainder rounding (plan §3.3)
- loaders of the baseline tables (Supplementary Files 2 / 3, L / N columns)
- reduced-panel rule helpers (plan WP2) and the four scores (plan WP3)
- preparation and harmonization wrappers: `prepare_subset`, `sva_nocov`,
  `combat_nocov`, `harmonize` (plan WP6 / WP7)
- `metrics_on_subset`, `gt_logfc_reference`, `gt_logfc_concordance` (plan WP6 / WP8)
- the docx ledger shared by r00 and r90 (plan WP0 / WP14)
"""

from __future__ import annotations

import gzip
import io
import json
import math
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Optional

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────

REVISION_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = REVISION_DIR.parent
BENCH_DIR: Path = REPO_ROOT / "harmonization-scripts"
METRICS_CODE_DIR: Path = REPO_ROOT / "harmonization-metrics-calculation"
INPUTS_DIR: Path = REVISION_DIR / "inputs"
OUTPUT_DIR: Path = REVISION_DIR / "output"
CACHE_DIR: Path = REVISION_DIR / "cache"

SUPP_FILE_2_PATH: Path = INPUTS_DIR / "Supplementary File 2.xlsx"
SUPP_FILE_3_PATH: Path = INPUTS_DIR / "Supplementary File 3.csv.gz"
# The blind-check concat (2026-09-05) is the only table with the Group L narrow-set
# and Group N columns for (almost) every approach. It is used for L and N ONLY; the
# 87 published metrics come from Supplementary File 3 (memory: 260527 is unusable).
LMN_TABLE_PATH: Path = (
    REPO_ROOT / "harmonization-metrics/metric_tables/metrics_comprehensive_260905.csv"
)

for _code_dir in (BENCH_DIR, METRICS_CODE_DIR):
    if str(_code_dir) not in sys.path:
        sys.path.insert(0, str(_code_dir))

# ── S3 layout ─────────────────────────────────────────────────────────────────

S3_BUCKET: str = os.environ.get("FL_S3_BUCKET", "")
S3_PREFIX: str = "FL_batch_correction"
# Overridable only for smoke tests (a scratch prefix), never for the real runs.
REVISION_S3_PREFIX: str = os.environ.get(
    "REVISION_S3_PREFIX", f"{S3_PREFIX}/revision_261029"
)
EXPERIMENTS: tuple[str, ...] = ("gradient", "v1", "bridging")

# 20_shambhala of Article 1 is shambhala_P0std_Q0std of the Shambhala cross-product
# (Nikit357/Shambhala2_fast), not the R package behind bench_shared's entry of the same
# name; these are the published settings (plan revision_pod_combobatch_image_plan_261101).
SHAMBHALA_CALIB_PREFIX: str = f"{S3_PREFIX}/calibration_datasets"
SHAMBHALA_P_FILE: str = "P0_standard.csv"
SHAMBHALA_Q_FILE: str = "Q0_standard.csv"
SHAMBHALA_SEED: int = 42  # published --random-seed
SHAMBHALA_K: int = 5  # published k-means clusters of CuBlock
SHAMBHALA_WORKERS: int = 16  # published --n-shambhala-workers
SHAMBHALA_TIMEOUT_S: int = 7200  # published --shambhala-timeout-s default


def s3_key_subset(experiment: str, subset_id: str, kind: str) -> str:
    """S3 key of a prepared subset: kind is 'exp' or 'ann'."""
    return f"{REVISION_S3_PREFIX}/{experiment}/prepared/{subset_id}__{kind}.tsv.gz"


def s3_key_harmonized(experiment: str, subset_id: str, arm: str) -> str:
    """S3 key of one harmonized matrix (post0 only: the revision never post-removes)."""
    return f"{REVISION_S3_PREFIX}/{experiment}/exp/{subset_id}__{arm}.tsv.gz"


def s3_key_run_record(experiment: str, subset_id: str, arm: str) -> str:
    """S3 key of the JSON run record (status, run time, fallback) of one job."""
    return f"{REVISION_S3_PREFIX}/{experiment}/runs/{subset_id}__{arm}.json"


def s3_key_revision_metrics(experiment: str, job_id: str) -> str:
    """S3 key of the metric JSON of one revision job (gradient, v1 or bridging)."""
    return f"{REVISION_S3_PREFIX}/{experiment}/metrics/{job_id}_metrics.json"


def s3_client() -> object:
    """Return a boto3 S3 client (credentials from ~/.aws, as in the benchmark pods)."""
    import boto3

    return boto3.client("s3")


def s3_exists(client: object, key: str) -> bool:
    """True if the key exists in the revision bucket."""
    import botocore.exceptions

    try:
        client.head_object(Bucket=S3_BUCKET, Key=key)  # type: ignore[attr-defined]
        return True
    except botocore.exceptions.ClientError:
        return False


def s3_list_keys(client: object, prefix: str) -> set[str]:
    """All keys under a prefix (paginated)."""
    keys: set[str] = set()
    paginator = client.get_paginator("list_objects_v2")  # type: ignore[attr-defined]
    for page in paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix):
        keys.update(obj["Key"] for obj in page.get("Contents", []))
    return keys


def s3_put_json(client: object, key: str, payload: dict) -> None:
    """Upload a JSON document (NaN written as null)."""
    body = json.dumps(_json_safe(payload), indent=1).encode()
    client.put_object(Bucket=S3_BUCKET, Key=key, Body=body)  # type: ignore[attr-defined]


def s3_get_json(client: object, key: str) -> dict:
    """Download a JSON document."""
    obj = client.get_object(Bucket=S3_BUCKET, Key=key)  # type: ignore[attr-defined]
    return json.loads(obj["Body"].read())


def s3_put_tsv_gz(client: object, key: str, frame: pd.DataFrame) -> None:
    """Upload a DataFrame as gzip TSV (index kept), the format of the benchmark."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as handle:
        frame.to_csv(handle, sep="\t")
    buffer.seek(0)
    client.upload_fileobj(buffer, S3_BUCKET, key)  # type: ignore[attr-defined]


def s3_get_tsv_gz(client: object, key: str) -> pd.DataFrame:
    """Download a gzip TSV written by `s3_put_tsv_gz` or by bench_shared."""
    buffer = io.BytesIO()
    client.download_fileobj(S3_BUCKET, key, buffer)  # type: ignore[attr-defined]
    buffer.seek(0)
    with gzip.open(buffer, "rb") as handle:
        return pd.read_csv(handle, sep="\t", index_col=0, low_memory=False)


def _json_safe(value: object) -> object:
    """Recursively replace NaN / inf / numpy scalars so json.dumps never fails."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


# ── Annotation conventions ────────────────────────────────────────────────────

BATCH_COL: str = "RNA_BATCH"
BIO_COL: str = "Diagnosis_cell_type_unified"
COHORT_COL: str = "COHORT_LABEL"
PLATFORM_COL: str = "PLATFORM_RNA"

# Normal B = Major_group in {Normal_B_cells, B_cells, Kassandra}. Never collapse diagnoses by
# substring (figures CLAUDE.md gotcha).
MAJOR_GROUP_3CLASS: dict[str, str] = {
    "Diffuse_Large_B_Cell_Lymphoma": "DLBCL",
    "Follicular_Lymphoma": "FL",
    "Normal_B_cells": "Normal B",
    "Kassandra": "Normal B",
    "B_cells": "Normal B",
}
MAJOR_GROUP_5CLASS: dict[str, str] = {
    **MAJOR_GROUP_3CLASS,
    "Burkitt_Lymphoma": "BL",
    "High_Grade_B_Cell_Lymphoma": "HGBCL",
}
DIAGNOSIS_ORDER: tuple[str, ...] = ("DLBCL", "FL", "Normal B")


def major_group(ann: pd.DataFrame, n_classes: int = 5) -> pd.Series:
    """Map `Major_group` to the 3-class (DLBCL / FL / Normal B) or 5-class labels."""
    mapping = MAJOR_GROUP_3CLASS if n_classes == 3 else MAJOR_GROUP_5CLASS
    return ann["Major_group"].map(mapping)


def load_s0_annotation(imp: str = "softimpute") -> pd.DataFrame:
    """
    The authoritative 7,174-sample annotation (prepared S3 copy of strategy S0).

    Cached in `cache/`; downloaded from S3 when missing.
    """
    path = CACHE_DIR / f"S0_no_removal__{imp}__ann.tsv.gz"
    if not path.exists():
        CACHE_DIR.mkdir(exist_ok=True)
        s3_client().download_file(  # type: ignore[attr-defined]
            S3_BUCKET,
            f"{S3_PREFIX}/prepared/S0_no_removal__{imp}__ann.tsv.gz",
            str(path),
        )
    return pd.read_csv(path, sep="\t", index_col=0, low_memory=False)


# ── Plain-word names for publication documents (plan §1.1) ────────────────────

PUBLICATION_NAMES: dict[str, str] = {
    # four scores and gates
    "L": "Marker correlation preservation",
    "N": "Cross-batch diagnosis prediction (macro-F1)",
    "gate_L": "Marker correlation threshold (ρ ≥ 0.7)",
    "gate_N": "Prediction non-inferiority check",
    "local_batch": "Local batch mixing",
    "local_biology": "Local diagnosis separation",
    "global_batch": "Global batch removal",
    "global_biology": "Global diagnosis retention",
    # D1 (Daniil 2026-11-08): the combined axes name their global + local origin, so
    # "batch removal" is never confused with the sample-removal strategies
    "batch_removal": "Batch mixing (global + local mean)",
    "biology_retention": "Diagnosis retention (global + local mean)",
    "batch_removal_short": "Batch mixing",
    "biology_retention_short": "Diagnosis retention",
    # selection
    "rule_front": "Selected by the rule",
    "visual_best": "Selected by visual inspection (submitted version)",
    "visual_check": "Visual check of the rule's front (revision)",
    "final_selection": "Recommended (rule front, accepted at the visual check)",
    "method_returned_input": "Method failed: returned its input unchanged",
    "bridging_biology": "Diagnosis separation on multi-diagnosis batches",
    "single_dx_batch": "Single-diagnosis batch",
    "bridging_batch": "Multi-diagnosis batch",
    # panel columns of Supplementary File 2
    "in_reduced_panel": "In the reduced metric panel",
    "cluster_id": "Correlation cluster",
    "representative_of": "Represents the metrics",
    "axis": "Score axis",
    "four_score_bar": "Score bar",
    # sheets of Supplementary File 3
    "main_benchmark": "Main benchmark",
    "confounding_gradient": "Confounding gradient",
    "leave_cohort_out": "Leave-cohort-out validation",
    # gradient
    "lambda": "Confounding level λ (0 = every batch balanced, 1 = one diagnosis per batch)",
    "L11_single_dx": "The 11 single-diagnosis batches",
    "cramers_v": "Cramér's V (batch × diagnosis)",
    "pct_single_dx": "% samples in single-diagnosis batches",
    # internal: r12 still writes the columns; not in publications (2026-11-08)
    "gt_logfc": "Agreement with batch-free fold changes",
    "replicate": "Replicate",
    "cap": "Samples per batch capped at 150",
    # validation
    "V1": "Leave-cohort-out validation",
    "LOBO": "Leave-one-batch-out",
    "train": "Training part",
    "test": "Test part",
    "chosen_on_train": "Chosen on the training part",
    # leave-cohort-out loss: "decrease", never "regret" (Daniil 2026-11-08)
    "regret": "Decrease vs the best approach on the test part",
    # covariate-free arms
    "04_sva_nocov": "SVA without the diagnosis covariate",
    "05_combat_nocov": "ComBat without the diagnosis covariate",
}

# Short display names of the methods (Supplementary Table S1 abbreviations).
METHOD_DISPLAY_NAMES: dict[str, str] = {
    "01_raw": "No harmonization",
    "02_median_scaling": "Median scaling",
    "03_limma": "limma",
    "04_sva": "SVA",
    "04_sva_nocov": PUBLICATION_NAMES["04_sva_nocov"],
    "05_combat": "ComBat",
    "05_combat_nocov": PUBLICATION_NAMES["05_combat_nocov"],
    "06_combat_seq": "ComBat-seq",
    "07_pycombat": "pyComBat",
    "08_inmoose_combatseq": "InMoose ComBat-seq",
    "09_ruv": "RUV",
    "10_mnn": "MNN",
    "11_harmony": "Harmony",
    "12_scanorama": "Scanorama",
    "13_fsmvn": "FSMVN",
    "14_qsmooth": "qsmooth",
    "15_fsqn_py": "FSQN Python",
    "16_fsqn_r": "FSQN R",
    "17_quantile": "Quantile normalization",
    "18_rank": "Rank normalization",
    "19_tdm": "TDM",
    "20_shambhala": "Shambhala-2",
    "21_harmonizr": "HarmonizR",
    "22_tmm": "TMM",
    "23_vst": "VST",
    "25_angel": "Angel",
    "26_xpn": "XPN",
    "27_dwd": "DWD",
    "28_npn": "NPN",
    "29_combat_ref": "M-ComBat",
    "31_ruv3prps": "RUV-III-PRPS",
    "33_amdbnorm": "AMDBNorm",
    "36_explobatch": "exploBATCH",
}

# Strategy codes of the submitted article (S0, A, B, C, D, E1–E3, F–K). They are part of
# the publication notation (Daniil, 2026-11-08, gates_review §10.6 A; plan §1.1 exception):
# figures and tables show "code · name", the text gives "name (code)" at the first mention
# in the Methods and the Results and then the code only. S0 = "No removal" (submitted name).
STRATEGY_CODES: dict[str, str] = {
    "S0_no_removal": "S0",
    "A_confirmed_bad": "A",
    "B_extended_bad": "B",
    "C_rnaseq_only": "C",
    "D_malignant_only": "D",
    "E1_iterative_r1": "E1",
    "E2_iterative_r2": "E2",
    "E3_iterative_r3": "E3",
    "F_microarray_only": "F",
    "G_affymetrix_only": "G",
    "H_affymetrix_extended": "H",
    "I_rare_batches_removed": "I",
    "J_ff_only": "J",
    "K_ffpe_only": "K",
}
STRATEGY_PLAIN_NAMES: dict[str, str] = {
    "S0_no_removal": "No removal",
    "A_confirmed_bad": "Confirmed bad batches removed",
    "B_extended_bad": "Extended bad batches removed",
    "C_rnaseq_only": "RNA-seq only",
    "D_malignant_only": "Malignant samples only",
    "E1_iterative_r1": "Iterative removal, round 1",
    "E2_iterative_r2": "Iterative removal, round 2",
    "E3_iterative_r3": "Iterative removal, round 3",
    "F_microarray_only": "Microarrays only",
    "G_affymetrix_only": "Affymetrix only",
    "H_affymetrix_extended": "Affymetrix extended",
    "I_rare_batches_removed": "Rare batches removed",
    "J_ff_only": "FF only",
    "K_ffpe_only": "FFPE only",
}
# Label of figures and tables: "code · name".
STRATEGY_DISPLAY_NAMES: dict[str, str] = {
    strat: f"{STRATEGY_CODES[strat]} · {name}" for strat, name in STRATEGY_PLAIN_NAMES.items()
}

ALL_STRATEGIES: tuple[str, ...] = tuple(STRATEGY_DISPLAY_NAMES)

# The 31 methods of the 2,234-approach analysis set (Supplementary File 3,
# pct_samples_allNA < 5). Decision D8: leave-cohort-out validation runs all of them.
ANALYSED_METHODS: tuple[str, ...] = (
    "01_raw",
    "02_median_scaling",
    "03_limma",
    "04_sva",
    "05_combat",
    "06_combat_seq",
    "07_pycombat",
    "08_inmoose_combatseq",
    "09_ruv",
    "10_mnn",
    "11_harmony",
    "12_scanorama",
    "13_fsmvn",
    "14_qsmooth",
    "15_fsqn_py",
    "16_fsqn_r",
    "17_quantile",
    "18_rank",
    "19_tdm",
    "20_shambhala",
    "21_harmonizr",
    "22_tmm",
    "23_vst",
    "25_angel",
    "26_xpn",
    "27_dwd",
    "28_npn",
    "29_combat_ref",
    "31_ruv3prps",
    "33_amdbnorm",
    "36_explobatch",
)

# Plan WP6 step 6.3: the fixed arm set of the confounding gradient (decided before
# running). 01_raw is first because it is the Group L reference of every other arm.
GRADIENT_ARMS: tuple[str, ...] = (
    "01_raw",
    "03_limma",
    "04_sva",
    "04_sva_nocov",
    "05_combat",
    "05_combat_nocov",
    "10_mnn",
    "13_fsmvn",
    "16_fsqn_r",
    "17_quantile",
    "33_amdbnorm",
    "11_harmony",
    # Added 2026-11-07 after the visual check (gate G4, Daniil): both are among the 22
    # selected approaches, so they are tested under confounding too. Post-hoc arms,
    # stated as such in the Methods; M-ComBat anchors on RNASeq_FF_PolyA, one of the
    # 5 gradient batches.
    "25_angel",
    "29_combat_ref",
)


def method_display_name(method: str) -> str:
    """Plain-word method name for publication documents."""
    return METHOD_DISPLAY_NAMES.get(method, method)


# ── Confounding statistics ────────────────────────────────────────────────────


def cramers_v(
    labels_a: Iterable, labels_b: Iterable, bias_correct: bool = True
) -> float:
    """
    Cramér's V of two label vectors; bias-corrected after Bergsma (2013) by default.

    Parameters
    ----------
    labels_a, labels_b
        Two categorical vectors of equal length (NaN pairs are dropped).
    bias_correct
        Apply the Bergsma (2013) correction of φ² and of the table dimensions.

    Returns
    -------
    V in [0, 1]; NaN when either variable has a single level.
    """
    from scipy.stats import chi2_contingency

    frame = pd.DataFrame({"a": list(labels_a), "b": list(labels_b)}).dropna()
    table = pd.crosstab(frame["a"], frame["b"])
    n_rows, n_cols = table.shape
    if n_rows < 2 or n_cols < 2:
        return float("nan")
    n_total = table.values.sum()
    chi2 = chi2_contingency(table.values, correction=False)[0]
    phi2 = chi2 / n_total
    if not bias_correct:
        return float(math.sqrt(phi2 / min(n_rows - 1, n_cols - 1)))
    phi2_corrected = max(0.0, phi2 - (n_rows - 1) * (n_cols - 1) / (n_total - 1))
    rows_corrected = n_rows - (n_rows - 1) ** 2 / (n_total - 1)
    cols_corrected = n_cols - (n_cols - 1) ** 2 / (n_total - 1)
    denominator = min(rows_corrected - 1, cols_corrected - 1)
    return float(math.sqrt(phi2_corrected / denominator)) if denominator > 0 else 0.0


def adjusted_mutual_info(labels_a: Iterable, labels_b: Iterable) -> float:
    """Adjusted mutual information (scikit-learn), NaN pairs dropped."""
    from sklearn.metrics import adjusted_mutual_info_score

    frame = pd.DataFrame({"a": list(labels_a), "b": list(labels_b)}).dropna()
    return float(
        adjusted_mutual_info_score(frame["a"].astype(str), frame["b"].astype(str))
    )


# ── Confounding gradient designs (plan §3.2–§3.3) ─────────────────────────────

GRADIENT_CAP: int = 150
GRADIENT_LAMBDAS: tuple[float, ...] = tuple(round(0.1 * i, 1) for i in range(11))
GRADIENT_REPLICATES: tuple[int, ...] = (1, 2, 3)
# a(b): the assigned diagnosis of each of the five gradient batches (plan §3.2).
GRADIENT_ASSIGNED_DIAGNOSIS: dict[str, str] = {
    "GPL570_FF_Unknown": "Normal B",
    "GPL570_Unknown_Unknown": "DLBCL",
    "GPL96+97_FF_Unknown": "FL",
    "GPL96_FF_Unknown": "FL",
    "RNASeq_FF_PolyA": "DLBCL",
}


def gradient_batch_size(
    cell_counts: dict[str, int], assigned: str, cap: Optional[int]
) -> int:
    """
    n_b = min(cap, 3 · min_g c_{b,g}, c_{b,a(b)})  (plan §3.3).

    Parameters
    ----------
    cell_counts
        Available samples per diagnosis g in batch b.
    assigned
        a(b), the assigned diagnosis of the batch.
    cap
        Cap per batch (150, decision D9) or None for the uncapped sensitivity design.
    """
    candidates = [3 * min(cell_counts.values()), cell_counts[assigned]]
    if cap is not None:
        candidates.append(cap)
    return int(min(candidates))


def largest_remainder_round(targets: dict[str, float], total: int) -> dict[str, int]:
    """
    Round non-negative targets to integers that sum to `total` (largest remainder).

    Ties in the remainder are broken by the order of `targets` (deterministic).
    """
    floors = {key: int(math.floor(value + 1e-9)) for key, value in targets.items()}
    missing = total - sum(floors.values())
    remainders = sorted(
        targets,
        key=lambda key: (-(targets[key] - floors[key]), list(targets).index(key)),
    )
    for key in remainders[:missing]:
        floors[key] += 1
    return floors


def gradient_cell_targets(
    batch_size: int, assigned: str, lam: float, groups: Iterable[str] = DIAGNOSIS_ORDER
) -> dict[str, int]:
    """
    n_{b,g}(λ) = n_b · [(1 − λ)/3 + λ · 1{g = a(b)}], rounded by largest remainder.
    """
    groups = list(groups)
    raw = {
        g: batch_size
        * ((1.0 - lam) / len(groups) + lam * (1.0 if g == assigned else 0.0))
        for g in groups
    }
    return largest_remainder_round(raw, batch_size)


def gradient_design_id(lam: float, replicate: int, cap: Optional[int]) -> str:
    """Design identifier, e.g. 'grad_cap150_l0.3_r1' or 'grad_nocap_l1.0_r1'."""
    cap_tag = f"cap{cap}" if cap is not None else "nocap"
    return f"grad_{cap_tag}_l{lam:.1f}_r{replicate}"


SINGLE_DX_DESIGN_ID: str = "L11_single_dx"


def build_gradient_design(
    ann: pd.DataFrame, lam: float, replicate: int, cap: Optional[int]
) -> pd.DataFrame:
    """
    Draw the samples of one gradient design (plan §3.3).

    The draw is nested: for one replicate, each (batch, diagnosis) pool is permuted once
    with the seed = replicate number, and a design takes the first n_{b,g}(λ) samples of
    that permutation. Designs of the same replicate therefore differ only by the
    samples added to or removed from each cell along λ, which keeps sampling noise out
    of the λ curve; the replicates differ in which samples are drawn.

    Parameters
    ----------
    ann
        S0 annotation (needs RNA_BATCH and Major_group).
    lam
        Confounding level λ in [0, 1].
    replicate
        Replicate number (1–3), used as the random seed.
    cap
        Per-batch cap (150) or None.

    Returns
    -------
    DataFrame indexed by sample ID with columns RNA_BATCH, diagnosis_3class, cell_target.
    """
    diagnosis = major_group(ann, n_classes=3)
    rows: list[pd.DataFrame] = []
    for batch_index, (batch, assigned) in enumerate(
        GRADIENT_ASSIGNED_DIAGNOSIS.items()
    ):
        in_batch = ann.index[ann[BATCH_COL] == batch]
        pools = {g: in_batch[diagnosis.loc[in_batch] == g] for g in DIAGNOSIS_ORDER}
        counts = {g: len(pool) for g, pool in pools.items()}
        batch_size = gradient_batch_size(counts, assigned, cap)
        targets = gradient_cell_targets(batch_size, assigned, lam)
        for group_index, g in enumerate(DIAGNOSIS_ORDER):
            if targets[g] > counts[g]:
                raise AssertionError(
                    f"infeasible cell {batch} × {g}: need {targets[g]}, have {counts[g]}"
                )
            rng = np.random.default_rng([replicate, batch_index, group_index])
            order = rng.permutation(np.sort(pools[g].to_numpy()))
            chosen = order[: targets[g]]
            rows.append(
                pd.DataFrame(
                    {
                        BATCH_COL: batch,
                        "diagnosis_3class": g,
                        "cell_target": targets[g],
                    },
                    index=pd.Index(chosen, name="sample_id"),
                )
            )
    return pd.concat(rows)


def design_confounding(
    ann: pd.DataFrame, sample_ids: Iterable[str]
) -> dict[str, float]:
    """Measured confounding of a design: V (major group, 15-level dx), AMI, uncorrected V."""
    sub = ann.loc[list(sample_ids)]
    group5 = major_group(sub, n_classes=5)
    return {
        "n_samples": int(len(sub)),
        "n_batches": int(sub[BATCH_COL].nunique()),
        "cramers_v_major_group": cramers_v(sub[BATCH_COL], group5),
        "cramers_v_major_group_uncorrected": cramers_v(
            sub[BATCH_COL], group5, bias_correct=False
        ),
        "cramers_v_diagnosis": cramers_v(sub[BATCH_COL], sub[BIO_COL]),
        "ami_major_group": adjusted_mutual_info(sub[BATCH_COL], group5),
    }


def single_diagnosis_batches(ann: pd.DataFrame) -> list[str]:
    """RNA_BATCH levels whose samples all share one Diagnosis_cell_type_unified level."""
    n_levels = ann.groupby(BATCH_COL)[BIO_COL].nunique()
    return sorted(n_levels.index[n_levels == 1])


# ── Baseline tables ───────────────────────────────────────────────────────────

APPROACH_KEYS: list[str] = ["strat", "imp", "method", "post_rm"]
L_SCORE_COL: str = "mk_rho_mean_all_genes_narrow_set"
N_SCORE_COL: str = "pv_lobo3_f1_macro_mean"
N_NULL_MEAN_COL: str = "pv_lobo3_f1_macro_perm_mean"
N_NULL_STD_COL: str = "pv_lobo3_f1_macro_perm_std"
N_PVALUE_COL: str = "pv_lobo3_f1_perm_pvalue"
# Two-class version of N (DLBCL vs FL, Normal B left out). Gate G2 (Daniil, 2026-11-03):
# used by gate N for strategies that keep almost no Normal B (TWO_CLASS_N_STRATEGIES),
# so that they are not judged on a 3-class task with an empty third class.
N2_SCORE_COL: str = "pv_lobo2_f1_macro_mean"
N2_NULL_MEAN_COL: str = "pv_lobo2_f1_macro_perm_mean"
N2_NULL_STD_COL: str = "pv_lobo2_f1_macro_perm_std"
N2_PVALUE_COL: str = "pv_lobo2_f1_perm_pvalue"
TWO_CLASS_N_STRATEGIES: tuple[str, ...] = ("D_malignant_only",)
# 20_shambhala of Supplementary File 3 = shambhala_P0std_Q0std of the blind-check table
# (same matrices: the published metrics agree exactly on all 84 approaches, checked
# 2026-11-03). The blind check computed L / N for it under the cross-product name.
LMN_METHOD_ALIASES: dict[str, str] = {"shambhala_P0std_Q0std": "20_shambhala"}


def main_benchmark_matrix_key(strat: str, imp: str, method: str, post_rm: bool) -> str:
    """S3 key of a published harmonized matrix (20_shambhala is stored under its
    cross-product name shambhala_P0std_Q0std)."""
    stored = {v: k for k, v in LMN_METHOD_ALIASES.items()}.get(method, method)
    return f"{S3_PREFIX}/exp/{strat}__{imp}__{stored}__post{int(post_rm)}.tsv.gz"
LN_COLUMNS: list[str] = [
    L_SCORE_COL,
    "mk_rho_mean_all_genes",
    N_SCORE_COL,
    N_NULL_MEAN_COL,
    N_NULL_STD_COL,
    N_PVALUE_COL,
    "pv_lobo3_n_folds_multiclass",
    N2_SCORE_COL,
    N2_NULL_MEAN_COL,
    N2_NULL_STD_COL,
    N2_PVALUE_COL,
]


def load_metric_polarity() -> pd.DataFrame:
    """`Metric_polarity` sheet of Supplementary File 2 (344 metrics), indexed by Metric."""
    return pd.read_excel(SUPP_FILE_2_PATH, sheet_name="Metric_polarity").set_index(
        "Metric"
    )


def load_supp_file_3(analysis_set_only: bool = False) -> pd.DataFrame:
    """
    Supplementary File 3 (2,407 approaches × 93 columns), the authoritative 87 metrics.

    The analysis set is `pct_samples_allNA < 5` (2,234 approaches).
    """
    table = pd.read_csv(SUPP_FILE_3_PATH)
    table["post_rm"] = table["post_rm"].astype(bool)
    table["in_analysis_set"] = table["pct_samples_allNA"] < 5
    return table[table["in_analysis_set"]].copy() if analysis_set_only else table


def load_ln_columns() -> pd.DataFrame:
    """L (marker correlation) and N (cross-batch prediction) columns per approach."""
    table = pd.read_csv(
        LMN_TABLE_PATH, usecols=APPROACH_KEYS + LN_COLUMNS, low_memory=False
    )
    table["post_rm"] = (
        table["post_rm"].astype(str).str.lower().isin(["true", "1", "1.0"])
    )
    table = table[~table["method"].isin(set(LMN_METHOD_ALIASES.values()))]
    table["method"] = table["method"].replace(LMN_METHOD_ALIASES)
    return table.drop_duplicates(APPROACH_KEYS)


# Supplementary File 3 stores 6 decimals, so "equal" means equal at that precision.
IDENTITY_TOLERANCE: float = 5e-7
IDENTITY_MIN_METRICS: int = 4
# Deterministic, continuous metrics (no embedding, no subsampling): an unchanged matrix
# gives exactly the raw values; coarse metrics (kBET, % NA) agree by chance and UMAP /
# tSNE metrics vary between runs of the same matrix, so they are not used.
IDENTITY_METRICS: list[str] = [
    "PCReg_RNA_BATCH",
    "PCReg_Diagnosis_cell_type_unified",
    "asw_batch_norm_RNA_BATCH",
    "asw_bio_norm_Diagnosis_cell_type_unified",
]


def flag_identical_to_raw(
    table: pd.DataFrame,
    metric_columns: Optional[list[str]] = None,
    group_keys: tuple[str, ...] = ("strat", "imp", "post_rm"),
) -> pd.Series:
    """
    True where an approach is the unharmonized data under a method's name.

    Gate G2 choice 5 (Daniil, 2026-11-03): two frozen methods catch their own failure
    and return the input matrix with status "ok" (SVA: "sva() failed … returning
    uncorrected data"; exploBATCH without its R dependency fMM). Such an approach is a
    method failure, not a candidate. Mechanical criterion: every metric of
    `metric_columns` that both rows have (at least IDENTITY_MIN_METRICS of them) equals
    the value of the `01_raw` row with the same `group_keys` within IDENTITY_TOLERANCE.
    `01_raw` itself is never flagged. Default columns: IDENTITY_METRICS.
    """
    metric_columns = [c for c in (metric_columns or IDENTITY_METRICS) if c in table]
    keys = list(group_keys)
    flags = pd.Series(False, index=table.index)
    if len(metric_columns) < IDENTITY_MIN_METRICS:
        return flags
    raw = table[table["method"] == "01_raw"].drop_duplicates(keys).set_index(keys)
    for index, row in table.iterrows():
        if row["method"] == "01_raw":
            continue
        key = tuple(row[k] for k in keys)
        if key not in raw.index:
            continue
        reference = raw.loc[key, metric_columns].astype(float)
        values = row[metric_columns].astype(float)
        both = values.notna() & reference.notna()
        if both.sum() < IDENTITY_MIN_METRICS:
            continue
        flags[index] = bool(
            (np.abs(values[both] - reference[both]) <= IDENTITY_TOLERANCE).all()
        )
    return flags


# ── Reduced panel helpers (plan WP2) ──────────────────────────────────────────

ANNOTATION_COLUMNS: tuple[str, ...] = (
    "Diagnosis_cell_type_unified",
    "RNA_BATCH",
    "PLATFORM_RNA",
    "RNASEQ_SOURCE",
    "COHORT_LABEL",
    "Major_group",
    "TUMOR_NORMAL",
)
PANEL_COLUMNS: tuple[str, ...] = ("RNA_BATCH", "Diagnosis_cell_type_unified", "none")


def metric_annotation_column(metric: str) -> str:
    """Annotation column a metric is computed on ('none' when it has none)."""
    for column in ANNOTATION_COLUMNS:
        if metric.endswith("_" + column):
            return column
    return "none"


# Metrics with no annotation column: which side of the batch / biology split they are on.
NO_COLUMN_ROLE: dict[str, str] = {
    "wm_mean_batch": "batch removal",
    "wm_mean_bio": "biology retention",
    "wm_ratio_bio_batch": "neither",
    "ks_cohort_within_batch_frac_sig": "batch removal",
    "ks_cohort_within_batch_mean_D": "batch removal",
}


def metric_axis(metric: str, metric_group: str, metric_type: str) -> tuple[str, str]:
    """
    Score axis of a metric: (scope, role).

    scope: Global | Local | Distributional | Coverage (from `Metric type`; E and K are
    Coverage). role: batch removal | biology retention | neither. Group D counts as
    "batch removal / Global" in the four-score bars and group K as "neither" (plan WP2
    rule 5); that mapping is applied in `four_score_bar`.
    """
    scope = {
        "Global": "Global",
        "Local": "Local",
        "Distributional similarity": "Distributional",
        "Other": "Coverage",
    }.get(metric_type, metric_type)
    column = metric_annotation_column(metric)
    if column == "RNA_BATCH":
        role = "batch removal"
    elif column == "Diagnosis_cell_type_unified":
        role = "biology retention"
    elif metric_group in {"E", "K"}:
        role = "neither"
    else:
        role = NO_COLUMN_ROLE.get(metric, "neither")
    return scope, role


def four_score_bar(scope: str, role: str) -> Optional[str]:
    """Which of the four bars (global_batch … local_biology) an axis feeds, if any."""
    if role == "neither" or scope == "Coverage":
        return None
    side = "batch" if role == "batch removal" else "biology"
    level = "local" if scope == "Local" else "global"
    return f"{level}_{side}"


def polarity_adjust(table: pd.DataFrame, polarity: pd.Series) -> pd.DataFrame:
    """Multiply every metric by its polarity so that higher is always better."""
    return table[polarity.index].mul(polarity, axis=1)


def minmax_scale(table: pd.DataFrame) -> pd.DataFrame:
    """Column-wise min-max scaling to [0, 1] (constant columns become 0.5)."""
    low, high = table.min(), table.max()
    span = (high - low).replace(0, np.nan)
    scaled = (table - low) / span
    for column in span.index[span.isna()]:
        scaled[column] = np.where(table[column].notna(), 0.5, np.nan)
    return scaled


def abs_spearman(table: pd.DataFrame) -> pd.DataFrame:
    """|Spearman ρ| between columns, pairwise complete observations."""
    return table.rank().corr(method="pearson", min_periods=30).abs()


def complete_linkage_clusters(abs_rho: pd.DataFrame, cut: float) -> pd.Series:
    """Clusters at distance 1 − |ρ| ≤ cut (complete linkage). Returns metric → id."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    distance = (1.0 - abs_rho.fillna(0.0)).clip(lower=0.0)
    np.fill_diagonal(distance.values, 0.0)
    condensed = squareform(distance.values, checks=False)
    tree = linkage(condensed, method="complete")
    ids = fcluster(tree, t=cut, criterion="distance")
    return pd.Series(ids, index=abs_rho.index, name="cluster_id")


def medoid(metrics: list[str], abs_rho: pd.DataFrame) -> str:
    """Metric with the highest summed |ρ| to the other metrics of the list."""
    if len(metrics) == 1:
        return metrics[0]
    block = abs_rho.loc[metrics, metrics]
    return str(block.sum(axis=1).idxmax())


# ── Four scores (plan WP3) and Pareto front (plan WP4) ─────────────────────────

FOUR_SCORE_BARS: tuple[str, ...] = (
    "global_batch",
    "global_biology",
    "local_batch",
    "local_biology",
)


def pareto_front(points: pd.DataFrame, columns: list[str]) -> pd.Series:
    """
    Non-dominated rows (maximisation on every column). Rows with NaN are never on it.
    """
    values = points[columns].to_numpy(dtype=float)
    valid = ~np.isnan(values).any(axis=1)
    on_front = np.zeros(len(points), dtype=bool)
    for i in np.flatnonzero(valid):
        others = values[valid]
        dominated = (
            (others >= values[i]).all(axis=1) & (others > values[i]).any(axis=1)
        ).any()
        on_front[i] = not dominated
    return pd.Series(on_front, index=points.index)


def pareto_layers(points: pd.DataFrame, columns: list[str]) -> pd.Series:
    """
    Non-dominated sorting depth: 1 = Pareto front, 2 = front after removing layer 1, ….

    Rows with NaN on any column get NaN. Used to turn the rule's front into a full
    ranking (layer, then the scaled Local-batch bar) for Kendall τ and top-k checks.
    """
    layers = pd.Series(np.nan, index=points.index)
    remaining = points[points[columns].notna().all(axis=1)]
    depth = 1
    while not remaining.empty:
        front = pareto_front(remaining, columns)
        layers[front.index[front]] = depth
        remaining = remaining[~front]
        depth += 1
    return layers


def rule_order(
    scores: pd.DataFrame,
    candidate_col: str = "candidate",
    axes: tuple[str, str] = ("batch_removal", "biology_retention"),
    tiebreak: str = "local_batch_scaled",
) -> pd.Series:
    """
    Full ranking (1 = best) in the order of the selection rule.

    Candidates (both gates passed) come first, then the rest; inside each part the
    Pareto layer on the two rule axes, then the tie-break bar (descending). Rows with a
    missing axis value are ranked last.
    """
    frame = scores.copy()
    frame["_not_candidate"] = ~frame[candidate_col].fillna(False).astype(bool)
    frame["_layer"] = np.nan
    for _, part in frame.groupby("_not_candidate"):
        frame.loc[part.index, "_layer"] = pareto_layers(part, list(axes))
    frame["_layer"] = frame["_layer"].fillna(np.inf)
    frame["_tie"] = -frame[tiebreak].fillna(-np.inf)
    ordered = frame.sort_values(["_not_candidate", "_layer", "_tie"]).index
    return pd.Series(np.arange(1, len(ordered) + 1), index=ordered).reindex(
        scores.index
    )


# Raw columns of the revision metric JSONs that become the four scores. They carry the
# published names because `add_published_names` renames the compute-code columns.
SCORE_SOURCE_COLUMNS: dict[str, str] = {
    "L": L_SCORE_COL,
    "N": N_SCORE_COL,
    "N_null_mean": N_NULL_MEAN_COL,
    "N_null_std": N_NULL_STD_COL,
    "N_perm_pvalue": N_PVALUE_COL,
    "N2": N2_SCORE_COL,
    "N2_null_mean": N2_NULL_MEAN_COL,
    "N2_null_std": N2_NULL_STD_COL,
    "N2_perm_pvalue": N2_PVALUE_COL,
}


def bar_scaling_reference(
    bar_headlines_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Headline metric, polarity and the min / max of each bar over the 2,234 approaches.

    New runs (gradient, leave-cohort-out) are scaled with this fixed reference, so that
    a scaled bar means the same thing in every experiment: 0 = worst and 1 = best value
    reached in the main benchmark (values outside the range fall outside [0, 1]).
    """
    path = bar_headlines_path or OUTPUT_DIR / "wp3/bar_headlines.tsv"
    headlines = pd.read_csv(path, sep="\t").set_index("bar")
    table = load_supp_file_3(analysis_set_only=True)
    rows = []
    for bar, row in headlines.iterrows():
        adjusted = table[row["headline_metric"]] * row["polarity"]
        rows.append(
            {
                "bar": bar,
                "headline_metric": row["headline_metric"],
                "polarity": int(row["polarity"]),
                "low": float(adjusted.min()),
                "high": float(adjusted.max()),
            }
        )
    return pd.DataFrame(rows).set_index("bar")


def score_runs(metrics: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """
    The four scores of new runs (one row per harmonized matrix) in the r03 layout.

    Parameters
    ----------
    metrics : one row per run, with the published metric columns of the JSONs.
    reference : `bar_scaling_reference()`.

    Returns
    -------
    The input columns plus L, N, N_null_*, N_perm_pvalue, the four bars (native unit),
    their `_scaled` versions, batch_removal and biology_retention.
    """
    scored = metrics.copy()
    for target, source in SCORE_SOURCE_COLUMNS.items():
        scored[target] = (
            pd.to_numeric(metrics[source], errors="coerce")
            if source in metrics
            else np.nan
        )
    for bar, row in reference.iterrows():
        column = row["headline_metric"]
        values = (
            pd.to_numeric(metrics[column], errors="coerce")
            if column in metrics
            else pd.Series(np.nan, index=metrics.index)
        )
        scored[bar] = values
        span = row["high"] - row["low"]
        scored[f"{bar}_scaled"] = (values * row["polarity"] - row["low"]) / span
    scored["batch_removal"] = scored[
        ["global_batch_scaled", "local_batch_scaled"]
    ].mean(axis=1, skipna=False)
    scored["biology_retention"] = scored[
        ["global_biology_scaled", "local_biology_scaled"]
    ].mean(axis=1, skipna=False)
    return scored


# ── Preparation and harmonization wrappers (plan WP6 / WP7) ───────────────────

NO_COVARIATE_COL: str = "__no_covariate__"


def load_raw_data(cache_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Raw expression + annotation through the frozen `bench_shared.load_data`."""
    from bench_shared import load_data

    return load_data(cache_path=cache_path)


def prepare_subset(
    sample_ids: list[str], comb_exp: pd.DataFrame, ann_s0: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    softImpute preparation of a sample subset, as `run_prep_job.py` does for a strategy.

    The frozen steps, in the frozen order: `prepare_dataset_imputed(method="softimpute")`
    (genes with > 20 % NA in THIS subset dropped, softImpute on the rest) and then
    `log_transform_by_cohort`. The annotation rows are the S0 prepared annotation, so the
    revision uses the same labels as the 2,234-approach table. If softImpute fails, the
    frozen fallback of run_prep_job is applied (strict: genes with any NA dropped) and
    recorded.

    Returns
    -------
    (expression, annotation, record) — record holds n_samples, n_genes, imputation used.
    """
    from bench_shared import (
        log_transform_by_cohort,
        prepare_dataset,
        prepare_dataset_imputed,
    )

    ann_subset = ann_s0.loc[sample_ids]
    record: dict = {"n_samples_requested": len(sample_ids), "imputation": "softimpute"}
    try:
        exp_subset, ann_out = prepare_dataset_imputed(
            ann_subset, comb_exp, method="softimpute"
        )
    except Exception as error:  # the frozen run_prep_job fallback
        record["imputation"] = f"strict_fallback: {error!r}"[:500]
        exp_subset, ann_out = prepare_dataset(ann_subset, comb_exp)
    exp_subset = log_transform_by_cohort(exp_subset, ann_out.loc[exp_subset.index])
    ann_out = ann_out.loc[exp_subset.index]
    record.update(
        {"n_samples": int(exp_subset.shape[0]), "n_genes": int(exp_subset.shape[1])}
    )
    return exp_subset, ann_out, record


def _with_constant_covariate(ann: pd.DataFrame) -> pd.DataFrame:
    """Annotation copy with a one-level column, so the frozen functions drop the covariate."""
    out = ann.copy()
    out[NO_COVARIATE_COL] = "all"
    return out


def combat_nocov(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame, **_: object
) -> pd.DataFrame:
    """
    ComBat without the diagnosis covariate.

    The frozen `normalize_combat` already runs with `mod = NULL` when the biology column
    has one level (bench_shared, "running without covariate"); this wrapper hands it a
    constant column. No ComBat code is copied.
    """
    from bench_shared import normalize_combat

    return normalize_combat(
        exp_df,
        _with_constant_covariate(ann_df),
        batch_col=BATCH_COL,
        bio_col=NO_COVARIATE_COL,
    )


def sva_nocov(exp_df: pd.DataFrame, ann_df: pd.DataFrame, **_: object) -> pd.DataFrame:
    """
    SVA without the diagnosis covariate.

    Step 1: the frozen `normalize_sva` with a constant biology column, which makes it use
    the intercept-only model (`mod = ~1`). In that model mod = mod0, and the default
    iteratively re-weighted SVA ("irw") needs an F-test between the two, which has zero
    numerator degrees of freedom; the frozen function then catches the R error and
    returns the input unchanged. Step 2 (documented wrapper, plan WP6 step 6.3): if the
    output equals the input, run `sva(method = "two-step")`, which needs only `mod`, with
    the same number of surrogate variables (`num.sv`, intercept-only model) and remove
    them with `limma::removeBatchEffect(covariates = sv)`, exactly as the frozen function
    does. Which step produced the matrix is printed (captured in the run record).
    """
    from bench_shared import normalize_sva

    ann_const = _with_constant_covariate(ann_df)
    out = normalize_sva(exp_df, ann_const, bio_col=NO_COVARIATE_COL)
    if not np.allclose(out.to_numpy(), exp_df.loc[out.index, out.columns].to_numpy()):
        print("sva_nocov: frozen SVA (irw, mod = ~1) produced the correction")
        return out
    print("sva_nocov: frozen SVA returned the input; running sva(method='two-step')")
    return _sva_two_step_intercept_only(exp_df)


def _sva_two_step_intercept_only(exp_df: pd.DataFrame) -> pd.DataFrame:
    """Two-step SVA with mod = ~1, surrogate variables removed by limma (see sva_nocov)."""
    import rpy2.robjects as ro
    from rpy2.robjects.packages import importr

    from bench_shared import _py2rpy, _r_gc, _rpy2py

    sva_r, limma_r, base_r = importr("sva"), importr("limma"), importr("base")
    data_frame = ro.DataFrame({"x": ro.IntVector([1] * len(exp_df))})
    mod = ro.r["model.matrix"](ro.Formula("~1"), data=data_frame)
    r_mat = base_r.as_matrix(_py2rpy(exp_df.T))
    n_sv = int(sva_r.num_sv(r_mat, mod)[0])
    print(f"sva_nocov: num.sv = {n_sv}")
    if n_sv == 0:
        print("sva_nocov: 0 surrogate variables — returning uncorrected data")
        return exp_df.copy()
    sv_obj = sva_r.sva(r_mat, mod, n_sv=n_sv, method="two-step")
    svs = np.asarray(_rpy2py(sv_obj.rx2("sv")))
    svs = svs.reshape(-1, 1) if svs.ndim == 1 else svs
    if svs.shape[0] != len(exp_df):
        svs = svs.T
    result = limma_r.removeBatchEffect(
        r_mat,
        covariates=base_r.as_matrix(_py2rpy(pd.DataFrame(svs, index=exp_df.index))),
    )
    result_np = result if isinstance(result, np.ndarray) else _rpy2py(result)
    _r_gc()
    return pd.DataFrame(
        np.asarray(result_np).T, index=exp_df.index, columns=exp_df.columns
    )


_SHAMBHALA_CALIBRATION: dict[str, pd.DataFrame] = {}


def _shambhala_calibration(filename: str) -> pd.DataFrame:
    """P or Q calibration set from S3 (samples × genes), cached per process."""
    if filename not in _SHAMBHALA_CALIBRATION:
        obj = s3_client().get_object(  # type: ignore[attr-defined]
            Bucket=S3_BUCKET, Key=f"{SHAMBHALA_CALIB_PREFIX}/{filename}"
        )
        frame = pd.read_csv(io.BytesIO(obj["Body"].read()), index_col=0)
        if frame.isna().any().any():
            raise ValueError(f"Shambhala calibration {filename} contains NaN")
        _SHAMBHALA_CALIBRATION[filename] = frame
    return _SHAMBHALA_CALIBRATION[filename]


def shambhala_fast(
    exp_df: pd.DataFrame, ann_df: pd.DataFrame, **_: object
) -> pd.DataFrame:
    """
    20_shambhala as published: Shambhala2_fast with the P0 / Q0 standard calibration.

    Article 1's 20_shambhala is `shambhala_P0std_Q0std` of the Shambhala cross-product,
    made by Nikit357/Shambhala2_fast (Python + Octave), not by the R package behind the
    frozen bench_shared entry of the same name. This function repeats steps 3–4 of that
    run's worker (`harmonization_scripts/run_shambhala_job.py`) on one matrix with the
    published settings (`SHAMBHALA_*`; no speed-up flags): gene intersection of input,
    P and Q; genes with a NaN dropped; Q statistics; per-sample CuBlock + quantile
    normalization in Octave (`harmonize_parallel`); Q re-scaling. Shambhala uses no
    labels, so the annotation and the batch / biology columns are ignored.

    Parameters
    ----------
    exp_df
        Samples × genes, log2 expression.
    ann_df
        Annotation (unused; kept for the common harmonizer signature).

    Returns
    -------
    pd.DataFrame
        Samples × (input ∩ P ∩ Q) genes, as in the published matrices.
    """
    code_dir = os.environ.get("SHAMBHALA_FAST_DIR", "")
    if not (Path(code_dir) / "shambhala").is_dir():
        raise RuntimeError(
            f"Shambhala2_fast not found (SHAMBHALA_FAST_DIR={code_dir!r}); "
            "the pod clones it at start-up"
        )
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    from shambhala import na_handling, q_rescale  # type: ignore[import-not-found]
    from shambhala import parallel as shambhala_parallel  # type: ignore[import-not-found]

    p_t = _shambhala_calibration(SHAMBHALA_P_FILE).T
    q_t = _shambhala_calibration(SHAMBHALA_Q_FILE).T
    input_t = exp_df.T
    common = input_t.index.intersection(p_t.index).intersection(q_t.index)
    print(
        f"shambhala_fast: {len(common)} genes in input ∩ P ∩ Q "
        f"(input {input_t.shape[0]}, P {p_t.shape[0]}, Q {q_t.shape[0]})"
    )
    if len(common) == 0:
        raise ValueError("shambhala_fast: empty gene intersection with P / Q")
    clean_df, na_mask = na_handling.apply_na_strategy(
        input_t.loc[common].T, strategy="drop"
    )
    clean_t = clean_df.T
    p_kept = p_t.loc[common].loc[clean_t.index]
    rm, rs = q_rescale.compute_q_statistics(q_t.loc[common].loc[clean_t.index].T)
    harmonized_t = shambhala_parallel.harmonize_parallel(
        input_df=clean_t,
        p_df=p_kept,
        rm=rm,
        rs=rs,
        k=SHAMBHALA_K,
        n_workers=SHAMBHALA_WORKERS,
        octave_scripts_dir=str(Path(code_dir) / "octave"),
        octave_bin="octave",
        timeout_s=SHAMBHALA_TIMEOUT_S,
        random_seed=SHAMBHALA_SEED,
        fixed_clusters=None,
        python_cublock=False,
    )
    return na_handling.restore_na_genes(harmonized_t.T, na_mask)


def harmonizer(arm: str) -> Callable[..., pd.DataFrame]:
    """
    The function of one arm: a frozen METHODS entry or a revision wrapper.

    Wrappers: the covariate-free 04_sva_nocov / 05_combat_nocov, and 20_shambhala →
    `shambhala_fast` (the published implementation, see `SHAMBHALA_*`).
    """
    if arm == "04_sva_nocov":
        return sva_nocov
    if arm == "05_combat_nocov":
        return combat_nocov
    if arm == "20_shambhala":
        return shambhala_fast
    from bench_shared import METHODS

    return METHODS[arm][0]  # type: ignore[return-value]


def harmonize(arm: str, exp_df: pd.DataFrame, ann_df: pd.DataFrame) -> pd.DataFrame:
    """Run one arm with the benchmark's batch / biology columns (as run_norm_job does)."""
    return harmonizer(arm)(exp_df, ann_df, batch_col=BATCH_COL, bio_col=BIO_COL)


# ── Metrics on revision runs and subsets (plan WP6 step 6.5, WP8) ─────────────

# Groups of the reduced panel are A, B, C, D, E, G, H, I, K (plan §3.5); J is cheap and
# kept; F (variancePartition, slow) and M (rank agreement, not in the panel) are not run.
REVISION_METRIC_GROUPS: frozenset[str] = frozenset("ABCDEGHIJKLN")
# WP8 bridging check: Diagnosis metrics of the panel live in groups A, B, G, H, I.
BRIDGING_METRIC_GROUPS: frozenset[str] = frozenset("ABGHI")


def metrics_on_subset(
    exp_df: pd.DataFrame,
    ann_df: pd.DataFrame,
    groups: Iterable[str],
    ref_df: Optional[pd.DataFrame] = None,
    sample_ids: Optional[Iterable[str]] = None,
    n_perm: Optional[int] = None,
) -> dict:
    """
    The frozen `compute_all_metrics` on (optionally) a subset of the samples.

    Parameters
    ----------
    exp_df, ann_df
        Harmonized matrix and its annotation (rows aligned by index).
    groups
        Metric groups to compute (letters A–N).
    ref_df
        01_raw reference of the same subset (Group L only).
    sample_ids
        Restrict to these samples before computing (WP8: multi-diagnosis batches).
    n_perm
        Permutations of the Group N negative control (default: the frozen N_PERM).
    """
    from compute_batch_metrics import N_PERM, compute_all_metrics

    common = exp_df.index.intersection(ann_df.index)
    if sample_ids is not None:
        common = common.intersection(pd.Index(list(sample_ids)))
    if ref_df is not None:
        common = common.intersection(ref_df.index)
    ref_aligned = ref_df.loc[common] if ref_df is not None else None
    result = compute_all_metrics(
        exp_df.loc[common],
        ann_df.loc[common],
        skip_slow=True,
        groups=set(groups),
        ref_df=ref_aligned,
        n_perm=N_PERM if n_perm is None else n_perm,
    )
    return add_published_names(result, exp_df.loc[common])


def add_published_names(result: dict, exp_df: pd.DataFrame) -> dict:
    """
    Add the Supplementary File 3 names that the compute code does not emit itself:
    `PCReg_<col>` (= the worker key `pcr_<col>`) and `pct_{genes,samples}_allNA`
    (group K reports the counts only). Without them the panel columns
    PCReg_RNA_BATCH / PCReg_Diagnosis… / pct_*_allNA would be missing.
    """
    out = dict(result)
    for key, value in result.items():
        if key.startswith("pcr_"):
            out["PCReg_" + key.removeprefix("pcr_")] = value
    n_samples, n_genes = exp_df.shape
    if "n_genes_allNA" in result and n_genes:
        out["pct_genes_allNA"] = 100.0 * result["n_genes_allNA"] / n_genes
    if "n_samples_allNA" in result and n_samples:
        out["pct_samples_allNA"] = 100.0 * result["n_samples_allNA"] / n_samples
    return out


GT_CONTRASTS: tuple[tuple[str, str], ...] = (("DLBCL", "FL"), ("Tumour", "Normal B"))


def _contrast_labels(ann: pd.DataFrame) -> pd.Series:
    return major_group(ann, n_classes=3)


def _logfc_ols(
    exp_df: pd.DataFrame,
    labels: pd.Series,
    batches: Optional[pd.Series],
    contrast: tuple,
) -> pd.Series:
    """
    Per-gene OLS log fold-change of one contrast, with batch as a factor if given.

    With batch in the model the coefficient is a within-batch contrast (batch cancels
    inside each batch), which is the batch-free reference of plan WP6 step 6.5.
    """
    group_a, group_b = contrast
    if group_a == "Tumour":
        mask = labels.isin(["DLBCL", "FL", "Normal B"])
        indicator = labels[mask].isin(["DLBCL", "FL"]).astype(float)
    else:
        mask = labels.isin([group_a, group_b])
        indicator = (labels[mask] == group_a).astype(float)
    samples = labels.index[mask]
    design = pd.DataFrame(
        {"intercept": 1.0, "contrast": indicator.values}, index=samples
    )
    if batches is not None:
        dummies = pd.get_dummies(batches.loc[samples], drop_first=True, dtype=float)
        design = pd.concat([design, dummies], axis=1)
    x = design.to_numpy()
    y = exp_df.loc[samples].to_numpy(dtype=float)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    return pd.Series(coef[1], index=exp_df.columns)


def gt_logfc_reference(raw_exp: pd.DataFrame, ann: pd.DataFrame) -> pd.DataFrame:
    """
    Batch-free reference log fold-changes (genes × contrasts) from the full raw data of
    the gradient batches: per-gene OLS with batch as a factor (plan WP6 step 6.5).
    """
    common = raw_exp.index.intersection(ann.index)
    labels = _contrast_labels(ann.loc[common]).dropna()
    exp_df = raw_exp.loc[labels.index].dropna(axis=1)
    batches = ann.loc[labels.index, BATCH_COL]
    return pd.DataFrame(
        {
            f"{a}_vs_{b}": _logfc_ols(exp_df, labels, batches, (a, b))
            for a, b in GT_CONTRASTS
        }
    )


def deming_slope(x: np.ndarray, y: np.ndarray, variance_ratio: float = 1.0) -> float:
    """Deming regression slope of y on x (errors in both; ratio of error variances δ)."""
    sxx, syy = np.var(x, ddof=1), np.var(y, ddof=1)
    sxy = np.cov(x, y, ddof=1)[0, 1]
    if sxy == 0:
        return float("nan")
    delta = variance_ratio
    return float(
        (syy - delta * sxx + math.sqrt((syy - delta * sxx) ** 2 + 4 * delta * sxy**2))
        / (2 * sxy)
    )


def gt_logfc_concordance(
    harmonized: pd.DataFrame, ann: pd.DataFrame, reference: pd.DataFrame
) -> dict:
    """
    Agreement with batch-free fold changes: the same contrasts computed on the harmonized
    matrix WITHOUT batch in the model, compared with the reference over the shared genes.

    Returns
    -------
    dict gt_rho_<contrast>, gt_slope_<contrast> (Deming, reference on x), gt_n_genes.
    """
    common = harmonized.index.intersection(ann.index)
    labels = _contrast_labels(ann.loc[common]).dropna()
    genes = harmonized.columns.intersection(reference.index)
    exp_df = harmonized.loc[labels.index, genes].dropna(axis=1)
    genes = exp_df.columns
    result: dict = {"gt_n_genes": int(len(genes))}
    from scipy.stats import spearmanr

    for group_a, group_b in GT_CONTRASTS:
        name = f"{group_a}_vs_{group_b}"
        has_both = (
            labels.isin(["DLBCL", "FL"]).any() and (labels == "Normal B").any()
            if group_a == "Tumour"
            else (labels == group_a).any() and (labels == group_b).any()
        )
        if not has_both or len(genes) < 10:
            result[f"gt_rho_{name}"] = float("nan")
            result[f"gt_slope_{name}"] = float("nan")
            continue
        observed = _logfc_ols(exp_df, labels, None, (group_a, group_b))
        expected = reference.loc[genes, name]
        result[f"gt_rho_{name}"] = float(spearmanr(expected, observed).statistic)
        result[f"gt_slope_{name}"] = deming_slope(
            expected.to_numpy(), observed.to_numpy()
        )
    return result


# ── Docx ledger (plan WP0 step 0.5, WP14) ─────────────────────────────────────

W_NS: str = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CHARS_PER_LINE: int = 90  # line estimate; the same constant for baseline and revision


def _paragraph_text(paragraph: object, view: str) -> str:
    """Accept-all ('accept') or reject-all ('reject') text of one w:p element."""
    pieces: list[str] = []
    for node in paragraph.iter():  # type: ignore[attr-defined]
        tag = node.tag.split("}")[-1]
        if tag not in {"t", "delText", "tab"}:
            continue
        inside_ins = any(a.tag == f"{{{W_NS}}}ins" for a in node.iterancestors())
        inside_del = any(a.tag == f"{{{W_NS}}}del" for a in node.iterancestors())
        if tag == "tab":
            pieces.append(" ")
        elif view == "accept" and tag == "t" and not inside_del:
            pieces.append(node.text or "")
        elif view == "reject" and (
            (tag == "t" and not inside_ins) or (tag == "delText" and not inside_ins)
        ):
            pieces.append(node.text or "")
    return "".join(pieces)


def docx_paragraphs(docx_path: Path, view: str = "accept") -> list[dict]:
    """
    Body paragraphs (including table cells) with style, text and whether in a table.
    """
    from lxml import etree

    with zipfile.ZipFile(docx_path) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    body = root.find(f"{{{W_NS}}}body")
    rows: list[dict] = []
    for paragraph in body.iter(f"{{{W_NS}}}p"):
        style_node = paragraph.find(f"{{{W_NS}}}pPr/{{{W_NS}}}pStyle")
        style = style_node.get(f"{{{W_NS}}}val") if style_node is not None else ""
        in_table = any(a.tag == f"{{{W_NS}}}tbl" for a in paragraph.iterancestors())
        rows.append(
            {
                "style": style,
                "text": _paragraph_text(paragraph, view),
                "in_table": in_table,
            }
        )
    return rows


def docx_ledger(docx_path: Path) -> tuple[pd.DataFrame, dict]:
    """
    Words and estimated lines per section of the accept-all text, plus item counts.

    Sections are Heading1 / Heading2 paragraphs; the estimated line count of a paragraph
    is ceil(characters / CHARS_PER_LINE). Main figures and tables are counted from their
    title paragraphs ("Figure N", "Table N"), supplementary items from the
    SUPPLEMENTARY DATA list ("Supplementary Figure N", "Supplementary File N").

    Returns
    -------
    (per-section table, totals dict)
    """
    paragraphs = docx_paragraphs(docx_path, view="accept")
    section, subsection = "FRONT", ""
    rows: list[dict] = []
    figures, tables, supp_figures, supp_files = set(), set(), set(), set()
    for paragraph in paragraphs:
        text = paragraph["text"].strip()
        style = paragraph["style"] or ""
        if style.lower().startswith("heading1"):
            section, subsection = text.upper()[:60], ""
            continue
        if style.lower().startswith("heading2"):
            subsection = text[:60]
            continue
        if not paragraph["in_table"]:
            if match := re.match(r"^Figure (\d+)\b", text):
                figures.add(int(match.group(1)))
            if match := re.match(r"^Table (\d+)\b", text):
                tables.add(int(match.group(1)))
            if match := re.match(r"^Supplementary Figure S?(\d+)\b", text):
                supp_figures.add(int(match.group(1)))
            if match := re.match(r"^Supplementary File (\d+)\b", text):
                supp_files.add(int(match.group(1)))
        words = len(text.split())
        lines = math.ceil(len(text) / CHARS_PER_LINE) if text else 0
        rows.append(
            {
                "section": section,
                "subsection": subsection,
                "in_table": paragraph["in_table"],
                "words": words,
                "lines": lines,
            }
        )
    detail = pd.DataFrame(rows)
    per_section = (
        detail.groupby(["section", "subsection", "in_table"], sort=False)[
            ["words", "lines"]
        ]
        .sum()
        .reset_index()
    )
    totals = {
        "words_total": int(detail["words"].sum()),
        "lines_total": int(detail["lines"].sum()),
        "words_body_no_tables": int(detail.loc[~detail["in_table"], "words"].sum()),
        "lines_body_no_tables": int(detail.loc[~detail["in_table"], "lines"].sum()),
        "main_figures": len(figures),
        "main_tables": len(tables),
        "supplementary_figures": len(supp_figures),
        "supplementary_files": len(supp_files),
    }
    return per_section, totals
