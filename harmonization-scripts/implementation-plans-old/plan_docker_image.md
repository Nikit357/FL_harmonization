# Docker Image Plan — Harmonization Benchmark

**Status:** PLAN ONLY — not yet implemented  
**Tracking:** Check off each section header as it is implemented.

---

## 0. Goals

| Goal | Mechanism |
|---|---|
| Python 3.11 + R 4.4 in one image | CRAN apt repo added to `python:3.11-slim` |
| All Python + R dependencies pre-installed | `requirements.txt` + `install_r_packages.R` |
| Input data from S3 (no `/uftp` access in pods) | `load_data()` rewritten to download from S3 |
| AWS credentials available in pod | Kubernetes Secret mounted at `/root/.aws` |
| S3-backed shared failed-jobs log | Per-pod S3 key + merge on startup/shutdown |
| Mock smoke-test for all methods | `test_mock.py` — runs every method on 80×200 synthetic data |
| Image published to ECR | Build + push pipeline at bottom of this doc |
| Pod stays alive for interactive/repeated use | `CMD ["sleep", "infinity"]`; attach via VSCode K8s extension or `kubectl exec` and run any Python script |

---

## 1. Files to Create

```
harmonization-scripts/
├── requirements.txt           NEW — Python dependency pins
├── install_r_packages.R       NEW — Installs all R packages inside Docker
├── Dockerfile                 NEW — Docker build recipe
├── test_mock.py               NEW — Smoke test: runs all 24 methods + 4 imputation on toy data
├── k8s/
│   ├── aws-credentials-secret.yaml    NEW — how to create the credentials Secret
│   └── pod.yaml               UPDATED — points to ECR image, mounts credentials
└── plan_docker_image.md       THIS FILE
```

---

## 2. Files to Modify

| File | What changes |
|---|---|
| `bench_shared.py` | `load_data()` downloads `comb_exp.tsv` and `comb_ann_unified.csv` from S3 instead of reading from `/uftp`. Two new constants: `S3_EXP_KEY`, `S3_ANN_KEY`. |
| `run_cross_product_parallel.py` | `FAILED_LOG_PATH` still used locally; two new helpers sync it to/from S3. **On startup** `_sync_failed_log_from_s3()` lists every `failed_jobs_*.txt` object under `{S3_PREFIX}/` (all previous pods, not just the current one) and merges them into the local log. **On shutdown** `_sync_failed_log_to_s3()` writes this pod's result to `failed_jobs_{POD_NAME}.txt`. |

---

## 3. Step 3.1 — `requirements.txt`

Pin only the minimum required versions; leave upper bounds open so the resolver stays flexible.

```text
# requirements.txt
boto3>=1.28
botocore>=1.31
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
rpy2>=3.5.11
harmonypy>=0.0.9
scanorama>=1.7
combat>=0.0.8          # from combat.pycombat import pycombat
inmoose>=0.3           # from inmoose.pycombat import pycombat_seq
psutil>=5.9
```

> **Note:** `matplotlib`, `seaborn`, `jupyter` are NOT listed — the harmonization
> scripts don't use them. Add only if a downstream use case needs them.

---

## 4. Step 4.1 — `install_r_packages.R`

R 4.4 (installed from the CRAN apt repo) ships with BiocManager for Bioconductor 3.20.

```r
# install_r_packages.R
# Run inside Docker via: Rscript /tmp/install_r_packages.R

options(
    repos      = c(CRAN = "https://cloud.r-project.org"),
    Ncpus      = parallel::detectCores(),
    warn       = 2   # treat warnings as errors during install
)

# ── BiocManager ───────────────────────────────────────────────────────────────
if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
BiocManager::install(version = "3.20", ask = FALSE, update = FALSE)

# ── CRAN packages ────────────────────────────────────────────────────────────
install.packages(c(
    "missForest",   # prepare_dataset_imputed method="missforest"
    "softImpute",   # prepare_dataset_imputed method="softimpute"
    "FSQN",         # normalize_fsqn_r
    "remotes"       # for GitHub installs below
), dependencies = TRUE)

# ── Bioconductor packages ────────────────────────────────────────────────────
BiocManager::install(c(
    "limma",        # normalize_limma, also used by normalize_sva
    "sva",          # normalize_sva, normalize_combat, normalize_combat_seq
    "RUVSeq",       # normalize_ruv
    "batchelor",    # normalize_mnn (fastMNN)
    "qsmooth",      # normalize_qsmooth
    "edgeR",        # normalize_tmm
    "DESeq2"        # normalize_vst
), ask = FALSE, update = FALSE)

# ── GitHub packages ───────────────────────────────────────────────────────────
# TDM: Training Distribution Matching (Thompson et al. 2016)
remotes::install_github("greenelab/TDM", upgrade = "never")

# HarmonizR (Voss et al. 2022) — NA-aware ComBat/limma wrapper
remotes::install_github("HSU-HPC/HarmonizR", upgrade = "never")

# ── Verification ──────────────────────────────────────────────────────────────
pkgs <- c("missForest", "softImpute", "FSQN",
          "limma", "sva", "RUVSeq", "batchelor",
          "qsmooth", "edgeR", "DESeq2",
          "TDM", "HarmonizR")
missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]
if (length(missing)) {
    stop("Failed to install: ", paste(missing, collapse = ", "))
} else {
    cat("All R packages installed successfully.\n")
}
```

> **Important:** `TDM` and `HarmonizR` are GitHub-only. The build will need
> internet access. If the build environment is air-gapped, pre-download the
> tarballs and `COPY` them into the image before installing.

---

## 5. Step 5.1 — `Dockerfile`

```dockerfile
# Dockerfile
# Base: official Python 3.11 slim (Debian 12 / bookworm)
FROM python:3.11-slim

# ── System dependencies ───────────────────────────────────────────────────────
# Build tools, R prerequisites, and headers needed by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 ca-certificates wget curl git \
        build-essential gfortran \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
        libhdf5-dev libbz2-dev liblzma-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Install R 4.4 from CRAN apt repo ────────────────────────────────────────
# The Debian bookworm default repo ships R 4.2; we need R 4.4 for Bioc 3.20.
RUN wget -qO- https://cloud.r-project.org/bin/linux/debian/marutter_pubkey.asc \
        | gpg --dearmor -o /usr/share/keyrings/r-project.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] \
        https://cloud.r-project.org/bin/linux/debian bookworm-cran44/" \
        > /etc/apt/sources.list.d/r-cran.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends r-base r-base-dev \
    && rm -rf /var/lib/apt/lists/*

# ── R packages ────────────────────────────────────────────────────────────────
COPY harmonization-scripts/install_r_packages.R /tmp/install_r_packages.R
RUN Rscript /tmp/install_r_packages.R

# ── Python packages ───────────────────────────────────────────────────────────
COPY harmonization-scripts/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# ── Copy scripts ─────────────────────────────────────────────────────────────
WORKDIR /app
COPY harmonization-scripts/ harmonization-scripts/

# ── Working directory and default command ────────────────────────────────────
# WORKDIR must match cwd used in subprocess.run() inside run_cross_product_parallel.py.
# No fixed ENTRYPOINT: the pod stays alive by default so any Python script can
# be run interactively via VSCode K8s extension or kubectl exec.
# Override CMD via pod spec `args:` for unattended batch runs, e.g.:
#   args: ["python", "run_cross_product_parallel.py", "--n-workers", "6", "--skip-if-exists"]
WORKDIR /app/harmonization-scripts
CMD ["sleep", "infinity"]
```

> **Building for mock test:** use `CMD ["--help"]` as default; run the mock test
> separately with `docker run <image> python test_mock.py`.

---

## 6. Step 6.1 — Changes to `bench_shared.py`

### 6.1.1 New constants (replace lines 33–36)

```python
# Old:
REMOTE_ROOT = "$FL_DATA_ROOT"
EXP_PATH    = f"{REMOTE_ROOT}/comb_exp.tsv"
ANN_PATH    = "~/B_cell_lymphomas/comb_ann_unified.csv"

# New — add after S3_PREFIX definition:
S3_BUCKET   = "$FL_S3_BUCKET"
S3_PREFIX   = "FL_batch_correction"

# S3 keys for the input data (overridable via env vars)
S3_EXP_KEY = os.environ.get(
    "BENCH_EXP_S3_KEY",
    f"{S3_PREFIX}/exp/comb_exp.tsv",       # set to the actual key after upload
)
S3_ANN_KEY = os.environ.get(
    "BENCH_ANN_S3_KEY",
    f"{S3_PREFIX}/exp/comb_ann_unified.csv",
)
```

> **Action required:** Confirm the exact S3 object keys after the upload.
> If the files were uploaded as `.tsv.gz` / `.csv.gz`, update the defaults
> or set the env vars in the pod YAML.

### 6.1.2 Replace `load_data()` body (lines 65–107)

Keep the function signature and docstring unchanged; replace only the file-reading block:

```python
def load_data(
    cache_path: str = "/tmp/bench_comb_data.pkl",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load raw expression and annotation — from S3 when running in a pod,
    from the pickle cache on subsequent calls within the same process.

    Parameters
    ----------
    cache_path
        Path for pickle cache. Pass empty string to disable.

    Returns
    -------
    tuple of (comb_exp, comb_ann)
    """
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    import boto3
    import gzip
    import io
    s3 = boto3.client("s3")

    # ── Expression matrix ─────────────────────────────────────────────────────
    print(f"Downloading expression from s3://{S3_BUCKET}/{S3_EXP_KEY} …", flush=True)
    obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_EXP_KEY)
    body = obj["Body"].read()
    if S3_EXP_KEY.endswith(".gz"):
        body = gzip.decompress(body)
    comb_exp = pd.read_csv(io.BytesIO(body), sep="\t", index_col=0)
    del body

    # ── Annotation ────────────────────────────────────────────────────────────
    print(f"Downloading annotation from s3://{S3_BUCKET}/{S3_ANN_KEY} …", flush=True)
    obj = s3.get_object(Bucket=S3_BUCKET, Key=S3_ANN_KEY)
    body = obj["Body"].read()
    if S3_ANN_KEY.endswith(".gz"):
        body = gzip.decompress(body)
    comb_ann = pd.read_csv(io.BytesIO(body), index_col=0)
    del body

    # ── Existing post-load processing (unchanged) ─────────────────────────────
    comb_ann["Diagnosis_with_coo"] = (
        comb_ann.Diagnosis_cell_type_general + "_" + comb_ann["coo_bg"].fillna("")
    )
    comb_ann["Diagnosis_unified_with_coo"] = (
        comb_ann.Diagnosis_cell_type_unified + "_" + comb_ann["coo_bg"].fillna("")
    )
    comb_ann.loc[
        comb_ann.index.isin(["PUB_Suntsova_GSE120795"]), "RNA_BATCH"
    ] = "RNASeq_FF_Unknown"

    common   = comb_exp.index.intersection(comb_ann.index)
    comb_exp = comb_exp.loc[common]
    comb_exp = comb_exp.loc[~comb_exp.index.duplicated(keep="first")]
    comb_ann = comb_ann.loc[~comb_ann.index.duplicated(keep="first")]

    result = (comb_exp, comb_ann)
    if cache_path:
        with open(cache_path, "wb") as f:
            pickle.dump(result, f, protocol=4)
    return result
```

> The `import boto3 / gzip / io` are placed inside the function to avoid
> top-level import failures when the module is used in environments without boto3
> (e.g., notebook imports). Alternatively, move them to the module top.

---

## 7. Step 7.1 — Changes to `run_cross_product_parallel.py`

### 7.1.1 S3-backed failed-jobs log

Add the following constants and two helpers after the existing
`_save_failed_log()` definition (around line 160). Do **not** remove
`FAILED_LOG_PATH` — it still drives the local file that workers read.

```python
import os

# S3 key for the per-pod failed-jobs file.
# Each pod writes its own file; startup merges all pods' files.
_POD_NAME = os.environ.get("POD_NAME", "local")
S3_FAILED_KEY_TEMPLATE = f"{S3_PREFIX}/failed_jobs_{{pod}}.txt"


def _s3_failed_key(pod: str = _POD_NAME) -> str:
    return S3_FAILED_KEY_TEMPLATE.format(pod=pod)


def _sync_failed_log_from_s3() -> None:
    """
    Download all per-pod failed_jobs_*.txt files from S3 and merge them
    into the local FAILED_LOG_PATH.

    Idempotent: safe to call even if no S3 files exist yet.
    """
    import boto3
    import botocore
    s3 = boto3.client("s3")
    prefix = f"{S3_PREFIX}/failed_jobs_"
    try:
        paginator = s3.get_paginator("list_objects_v2")
        pages     = paginator.paginate(Bucket=S3_BUCKET, Prefix=prefix)
        s3_keys: set[str] = set()
        for page in pages:
            for obj in page.get("Contents", []):
                body = s3.get_object(
                    Bucket=S3_BUCKET, Key=obj["Key"]
                )["Body"].read().decode()
                s3_keys |= {ln.strip() for ln in body.splitlines() if ln.strip()}
        if s3_keys:
            local_keys = _load_failed_log()
            merged = s3_keys | local_keys
            if merged != local_keys:
                _save_failed_log(merged)
                print(
                    f"[S3 sync] Merged {len(s3_keys)} keys from S3 with "
                    f"{len(local_keys)} local → {len(merged)} total.",
                    flush=True,
                )
    except botocore.exceptions.ClientError as exc:
        print(f"[S3 sync] Could not read failed_jobs from S3: {exc}", flush=True)


def _sync_failed_log_to_s3(keys: set[str]) -> None:
    """
    Upload the current pod's failed-job keys to its dedicated S3 object.

    Parameters
    ----------
    keys
        The full set of failed job keys after this run.
    """
    import boto3
    s3  = boto3.client("s3")
    key = _s3_failed_key()
    if keys:
        body = "\n".join(sorted(keys)).encode()
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
        print(
            f"[S3 sync] Uploaded {len(keys)} failed keys to "
            f"s3://{S3_BUCKET}/{key}",
            flush=True,
        )
    else:
        # Delete the pod's file if it has no failures (clean state)
        try:
            s3.delete_object(Bucket=S3_BUCKET, Key=key)
            print(f"[S3 sync] Cleared s3://{S3_BUCKET}/{key} (no failures).", flush=True)
        except Exception:
            pass
```

### 7.1.2 Wire the helpers into `main()`

In `main()`, right after the existing `_load_failed_log()` call (~line 482),
add the S3 download:

```python
    # NEW — merge in any failures recorded by other pods
    _sync_failed_log_from_s3()
    previously_failed = _load_failed_log()   # reload after merge
```

And right after the existing `_save_failed_log(updated_failed)` call (~line 529),
add the S3 upload:

```python
    # NEW — push this pod's failures to S3
    _sync_failed_log_to_s3(updated_failed)
```

---

## 8. Step 8.1 — `test_mock.py`

Place this file at `harmonization-scripts/test_mock.py`.
Run it inside the container with `python test_mock.py`.

```python
"""
Smoke test: run every normalization method and every imputation approach on
synthetic data to verify that all dependencies are correctly installed.

Exit code 0  → all methods pass (or raise the expected NotImplementedError).
Exit code 1  → at least one unexpected failure. 
"""
from __future__ import annotations

import sys
import traceback
import warnings

import numpy as np
import pandas as pd

from bench_shared import (
    BATCH_COL,
    BIO_COL,
    METHODS,
    prepare_dataset,
    prepare_dataset_imputed,
)


# ── Synthetic dataset ──────────────────────────────────────────────────────────
RNG      = np.random.default_rng(42)
N_SAMP   = 80      # ≥30 per batch needed by some methods
N_GENES  = 200
N_BATCH  = 3
N_DIAG   = 2

batches  = [f"BatchGPL{i}" for i in range(N_BATCH)]
diags    = [f"Diag{i}" for i in range(N_DIAG)]
sample_ids = [f"S{i:04d}" for i in range(N_SAMP)]

batch_labels = [batches[i % N_BATCH]  for i in range(N_SAMP)]
diag_labels  = [diags[i % N_DIAG]    for i in range(N_SAMP)]

exp = pd.DataFrame(
    RNG.exponential(5, size=(N_SAMP, N_GENES)).astype(float),
    index=sample_ids,
    columns=[f"GENE{j:04d}" for j in range(N_GENES)],
)

ann = pd.DataFrame(
    {
        BATCH_COL:              batch_labels,
        BIO_COL:                diag_labels,
        "Diagnosis_cell_type_general": diag_labels,
        "COHORT_LABEL":         batch_labels,
        "coo_bg":               ["GCB"] * N_SAMP,
    },
    index=sample_ids,
)

# ── Imputation smoke tests ─────────────────────────────────────────────────────
print("=" * 60)
print("IMPUTATION METHODS")
print("=" * 60)

imp_results: dict[str, str] = {}

# strict (no NAs needed)
try:
    e, a = prepare_dataset(ann, exp)
    assert e.shape[0] > 0
    imp_results["strict"] = "PASS"
except Exception:
    imp_results["strict"] = f"FAIL\n{traceback.format_exc()}"

# knn / missforest / softimpute — introduce ~10 % NAs first
exp_with_na = exp.copy()
mask = RNG.random(exp_with_na.shape) < 0.10
exp_with_na[mask] = np.nan

for imp in ("knn", "missforest", "softimpute"):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            e, a = prepare_dataset_imputed(ann, exp_with_na, method=imp)
        assert e.isna().sum().sum() == 0, "NAs remain after imputation"
        imp_results[imp] = "PASS"
    except Exception:
        imp_results[imp] = f"FAIL\n{traceback.format_exc()}"

for name, result in imp_results.items():
    status = result.split("\n")[0]
    print(f"  {name:<20} {status}")

# ── Normalization smoke tests ──────────────────────────────────────────────────
print()
print("=" * 60)
print("NORMALIZATION METHODS")
print("=" * 60)

norm_results: dict[str, str] = {}
e_strict, a_strict = prepare_dataset(ann, exp)

for key, (fn, harshness) in METHODS.items():
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            out = fn(e_strict, a_strict, batch_col=BATCH_COL, bio_col=BIO_COL)
        assert isinstance(out, pd.DataFrame), "Output is not a DataFrame"
        assert out.shape[0] > 0, "Output has 0 rows"
        norm_results[key] = "PASS"
    except NotImplementedError as exc:
        norm_results[key] = f"SKIP (NotImplementedError: {exc})"
    except Exception:
        norm_results[key] = f"FAIL\n{traceback.format_exc()}"

any_fail = False
for name, result in sorted(norm_results.items()):
    first_line = result.split("\n")[0]
    print(f"  {name:<30} {first_line}")
    if result.startswith("FAIL"):
        any_fail = True

# ── Detailed failure report ────────────────────────────────────────────────────
# Print full tracebacks for every failed method so the cause is immediately
# visible without having to rerun with extra flags.
failed_norm   = {k: v for k, v in norm_results.items() if v.startswith("FAIL")}
failed_imp    = {k: v for k, v in imp_results.items()  if v.startswith("FAIL")}
any_fail = bool(failed_norm or failed_imp)

if any_fail:
    print()
    print("=" * 60)
    print("FAILURE DETAILS")
    print("=" * 60)
    for name, tb in {**failed_imp, **failed_norm}.items():
        print(f"\n{'─' * 60}")
        print(f"FAILED: {name}")
        print("─" * 60)
        # tb is "FAIL\n<traceback text>" — strip the leading "FAIL\n"
        print(tb.split("\n", 1)[1] if "\n" in tb else tb)
    print()
    failed_names = sorted(failed_imp) + sorted(failed_norm)
    print(f"RESULT: {len(failed_names)} FAILURE(S): {', '.join(failed_names)}")
    sys.exit(1)
else:
    print()
    print("RESULT: All methods PASS or SKIP (expected). Dependencies OK.")
    sys.exit(0)
```

> The mock test does **not** touch S3. It exercises the R + Python code paths
> directly. `NotImplementedError` (RNA-seq-only methods on mixed batches) is
> treated as an expected skip, not a failure.

---

## 9. Step 9.1 — AWS Setup

### 9.1.1 Create ECR repository (run once)

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1   # adjust to your region

aws ecr create-repository \
    --repository-name fl-batch-correction \
    --region "$AWS_REGION"

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction"
echo "ECR URI: $ECR_URI"
```

### 9.1.2 Create the AWS Credentials Kubernetes Secret (run once per namespace)

```bash
kubectl create secret generic aws-credentials \
    --from-file=credentials=$HOME/.aws/credentials \
    --from-file=config=$HOME/.aws/config \
    --namespace ${K8S_NAMESPACE}

# Verify
kubectl get secret aws-credentials -n ${K8S_NAMESPACE}
```

If your `~/.aws/credentials` contains multiple profiles, the default profile
(or the one selected by `AWS_PROFILE`) is what boto3 will use.

---

## 10. Step 10.1 — Build and Push

```bash
cd ~/B_cell_lymphomas

# Log in to ECR
aws ecr get-login-password --region "$AWS_REGION" \
    | docker login --username AWS --password-stdin "$ECR_URI"

# Build (can take 20–40 min for R Bioconductor packages)
docker build \
    --tag fl-batch-correction:latest \
    --file harmonization-scripts/Dockerfile \
    .

# Smoke test inside the container before pushing
docker run --rm \
    -v "$HOME/.aws:/root/.aws:ro" \
    fl-batch-correction:latest \
    python test_mock.py

# Tag and push
docker tag fl-batch-correction:latest "${ECR_URI}:latest"
docker push "${ECR_URI}:latest"

# Tag a dated version for reproducibility
VERSION=$(date +%Y%m%d)
docker tag fl-batch-correction:latest "${ECR_URI}:${VERSION}"
docker push "${ECR_URI}:${VERSION}"
```

---

## 11. Step 11.1 — Kubernetes Manifests

### `k8s/pod.yaml`

This replaces `c6a.2xlarge-pod.yaml`. The key additions are:
- ECR image reference
- `POD_NAME` env var (for per-pod S3 failed-jobs file)
- AWS credentials volume mount
- `args:` that override the CMD tokens (dispatcher CLI flags)

```yaml
# k8s/pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: fl-batch-correction
  namespace: ${K8S_NAMESPACE}
spec:
  restartPolicy: Never
  shareProcessNamespace: true
  containers:
  - name: worker
    # Replace <ACCOUNT_ID> and <REGION> with actual values
    image: <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/fl-batch-correction:latest
    imagePullPolicy: Always

    # No `command` or `args` — the image default (sleep infinity) keeps the pod
    # alive so you can attach via VSCode Kubernetes extension or kubectl exec and
    # run any script with any parameters:
    #
    #   kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash
    #   # then inside the pod:
    #   python run_cross_product_parallel.py --n-workers 6 --skip-if-exists
    #   python test_mock.py
    #   python run_one_job.py --strat A_confirmed_bad --imp strict --method 16_fsqn_r
    #
    # For an unattended batch run, override with:
    #   command: ["python", "run_cross_product_parallel.py"]
    #   args: ["--n-workers", "6", "--skip-if-exists", "--memory-limit-gb", "12.0"]
    # and set restartPolicy: Never.

    env:
    - name: POD_NAME
      valueFrom:
        fieldRef:
          fieldPath: metadata.name
    # Optional: override default S3 data keys if the uploaded files have
    # different names or are compressed
    # - name: BENCH_EXP_S3_KEY
    #   value: "FL_batch_correction/exp/comb_exp.tsv.gz"
    # - name: BENCH_ANN_S3_KEY
    #   value: "FL_batch_correction/exp/comb_ann_unified.csv"

    resources:
      requests:
        cpu: "8"
        memory: "16Gi"
      limits:
        cpu: "8"
        memory: "16Gi"

    volumeMounts:
    - name: work
      mountPath: /workspace
    - name: aws-credentials
      mountPath: /root/.aws
      readOnly: true

  volumes:
  - name: work
    persistentVolumeClaim:
      claimName: fl-workspace
  - name: aws-credentials
    secret:
      secretName: aws-credentials

  tolerations:
    - key: node-group
      operator: Equal
      value: ${K8S_NAMESPACE}
      effect: NoSchedule
  nodeSelector:
    karpenter.k8s.aws/instance-family: c6a
```

> To run multiple pods in parallel (to split the 960-job grid), create
> multiple pods with different `metadata.name` values and non-overlapping
> `--strats` / `--methods` subsets passed via `args:`.

### `k8s/aws-credentials-secret.yaml`

Not a manifest to apply directly (it would store credentials in plaintext YAML).
Use the `kubectl create secret` command from Step 9.1.2 instead.
This file documents the structure for reference only:

```yaml
# k8s/aws-credentials-secret.yaml  — REFERENCE ONLY, do not commit with real credentials
# Generated by:
#   kubectl create secret generic aws-credentials \
#       --from-file=credentials=$HOME/.aws/credentials \
#       --from-file=config=$HOME/.aws/config -n ${K8S_NAMESPACE}
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: ${K8S_NAMESPACE}
type: Opaque
data:
  credentials: <base64-encoded ~/.aws/credentials>
  config:      <base64-encoded ~/.aws/config>
```

---

## 12. End-to-End Run Workflow

```
1.  Upload data to S3
    aws s3 cp comb_exp.tsv          s3://$FL_S3_BUCKET/FL_batch_correction/exp/comb_exp.tsv
    aws s3 cp comb_ann_unified.csv  s3://$FL_S3_BUCKET/FL_batch_correction/exp/comb_ann_unified.csv

2.  Build and push Docker image (Step 10.1)

3.  Create ECR + K8s Secret (Step 9.1)

4.  Edit k8s/pod.yaml — fill in <ACCOUNT_ID>, <REGION>, adjust --n-workers and --memory-limit-gb
    for the instance type (c6a.2xlarge = 8 vCPU / 16 GiB).

5.  Apply the pod:
    kubectl apply -f harmonization-scripts/k8s/pod.yaml

6.  Follow logs:
    kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}

7.  After the pod completes, load results in the notebook:
    from load_cross_product_results import load_metrics
    metrics_df = load_metrics()

8.  Failed jobs are visible in S3:
    aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/failed_jobs_
    # One file per pod run.  Merge them manually or with:
    aws s3 cp s3://.../failed_jobs_fl-batch-correction.txt failed_jobs.txt
```

---

## 13. Implementation Checklist

- [x] **3.1** Create `requirements.txt`
- [x] **4.1** Create `install_r_packages.R`; verified all `importr()` calls; updated BiocManager to 3.22 for R 4.5
- [x] **5.1** Create `Dockerfile`; CRAN repo corrected to `bookworm-cran40` (ships R 4.5.3); GPG key fetched via HTTPS keyserver
- [x] **6.1** Modify `bench_shared.py`: added `S3_EXP_KEY`/`S3_ANN_KEY` constants; rewrote `load_data()` with S3 download; fixed `softimpute` rpy2 numpy array conversion bug
- [x] **7.1** Modify `run_cross_product_parallel.py`: added `_sync_failed_log_from_s3()` and `_sync_failed_log_to_s3()`; wired into `main()`
- [x] **8.1** Create `test_mock.py`; passes locally — 22 PASS, 2 expected SKIP (shambhala/PEER)
- [ ] **9.1** Create ECR repo (requires `ecr:CreateRepository` — must be done by admin); create K8s credentials Secret (requires `kubectl` on local machine)
- [ ] **10.1** Build image locally (requires Docker); run `docker run ... python test_mock.py`; push to ECR
- [x] **11.1** Create `k8s/pod.yaml` and `k8s/aws-credentials-secret.yaml`; ECR URI pre-filled as `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest`
- [ ] **12** Apply pod; verify logs

---

## 14. Known Risks and Mitigations

| Risk | Mitigation |
|---|---|
| R package build takes >40 min and hits Docker layer cache on reruns | Run `docker build --cache-from` against the existing ECR image so the R layer is reused |
| `TDM` or `HarmonizR` GitHub repos become unavailable | Pre-download tarballs with `wget` in the Dockerfile; `install.packages(tarball_path)` |
| Two pods write `failed_jobs_{pod}.txt` at exactly the same time | No conflict — per-pod keys are independent; each pod only writes its own file |
| `comb_exp.tsv` is ~1.5 GB; S3 download can be slow in the pod | The pickle cache at `/tmp/bench_comb_data.pkl` handles this after the first download per pod lifetime. For warm caches across pod restarts, mount the PVC at `/tmp` or set `--cache-path /workspace/bench_comb_data.pkl` (add this CLI arg to `run_one_job.py` if needed) |
| `S3_EXP_KEY` default may not match the actual uploaded filename | Confirm with `aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/` and set `BENCH_EXP_S3_KEY` env var in the pod spec accordingly |
| rpy2 version incompatible with R 4.5 | Pinned `rpy2>=3.5.5` (tested and working); test during Docker build with `python -c "import rpy2; print(rpy2.__version__)"` |
| `softImpute::complete()` returns numpy array in R 4.5/rpy2 3.5.5 | Fixed in `bench_shared.py` line 407: guard with `isinstance(imp_mat, np.ndarray)` before calling `rpy2py()` |

---

## 15. Detailed TODO List

> Phases must be completed in order. Tasks within a phase can often be done in parallel.
> Check off each task as it is done; if a task reveals a new problem, add a sub-task inline.

---

### Phase 0 — Prerequisites & Verification
*Confirm the environment is ready before writing a single file.*

- [ ] **0.1** Verify Docker is installed and the daemon is running on the build machine (`docker info`) — **must run on local machine with Docker**
- [x] **0.2** Verified: `aws sts get-caller-identity` → account ${AWS_ACCOUNT_ID}, user daniil.nikitin, region us-east-1
- [x] **0.3** S3 access confirmed (`s3:GetObject`, `s3:PutObject`, `s3:ListBucket` all work). ECR create permission is absent — needs admin (see Phase 9.2 note)
- [ ] **0.4** Confirm `kubectl` has access to the `${K8S_NAMESPACE}` namespace — **must run on local machine with kubectl**
- [ ] **0.5** Confirm Karpenter node IAM role includes ECR pull permissions — **check with infra team**
- [x] **0.6** S3 input keys confirmed (uncompressed, no `.gz`):
  - `FL_batch_correction/exp/comb_exp.tsv` (1.9 GB)
  - `FL_batch_correction/exp/comb_ann_unified.csv` (6.9 MB)
  Defaults in `bench_shared.py` match exactly; no env var override needed.
- [ ] **0.7** Confirm GitHub is reachable from the Docker build machine — **test on local machine**

---

### Phase 1 — Python Dependency File
*Produces: `harmonization-scripts/requirements.txt`*

- [x] **1.1** Created `requirements.txt`
- [x] **1.2** All imports verified against installed packages: `combat` 0.3.3, `inmoose` 0.9.1, `harmonypy` 0.0.10, `scanorama` 1.7.4 — all import successfully
- [ ] **1.3** Dry-run install in throwaway venv — **run on local machine before Docker build**
- [ ] **1.4** Record resolved versions — **run `pip freeze` after Docker build** to capture pinned versions

---

### Phase 2 — R Package Installation Script
*Produces: `harmonization-scripts/install_r_packages.R`*

- [x] **2.1** Created `install_r_packages.R`; updated to BiocManager 3.22 (matches local R 4.5.3)
- [x] **2.2** All `importr()` calls audited; all 12 packages present locally (limma 3.66, sva 3.58, RUVSeq 1.44, batchelor 1.26, qsmooth 1.26, edgeR 4.8, DESeq2 1.50, missForest 1.6, softImpute 1.4, FSQN 0.0.1, TDM 0.3, HarmonizR 0.99.2)
- [x] **2.3** Changed `warn = 1` (not `warn = 2`) to avoid benign install warnings blocking the build
- [x] **2.4** All packages confirmed installed and functional in R 4.5.3 via `test_mock.py` run

---

### Phase 3 — Dockerfile
*Produces: `harmonization-scripts/Dockerfile`*

- [x] **3.1** Created `Dockerfile`. Key corrections vs plan: CRAN repo is `bookworm-cran40` (not `bookworm-cran44` — that repo 404s); GPG key fetched via `https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7` (old `marutter_pubkey.asc` URL also 404s)
- [x] **3.2** Created `.dockerignore` at project root; excludes `*.tsv`, `*.Rdata`, `*.h5ad`, `local_copy.zarr/`, `normal_B_cells/`, `cell_lines/`, `*.pkl`, `.git/`, etc.
- [x] **3.3** CRAN repo verified: `bookworm-cran40` serves R 4.5.3-1 (confirmed via `Packages.gz`)
- [x] **3.4** `WORKDIR /app/harmonization-scripts` matches `cwd=str(Path(__file__).parent)` ✓
- [x] **3.5** `COPY harmonization-scripts/ harmonization-scripts/` path confirmed correct relative to project root build context

---

### Phase 4 — Code Change: `bench_shared.py`
*Modifies: `bench_shared.py`*

- [x] **4.1** Added `S3_EXP_KEY` and `S3_ANN_KEY` constants; default keys match confirmed S3 paths
- [x] **4.2** `load_data()` now downloads from S3 with gzip auto-detection; `boto3` imported inside the function
- [x] **4.3** Removed `REMOTE_ROOT` and `EXP_PATH` constants
- [x] **4.4** Removed `ANN_PATH` constant
- [x] **4.5** `gzip` and `io` already at module top ✓; `boto3` imported inside `load_data()` ✓
- [x] **4.6** S3 keys verified by `aws s3 ls`; also fixed bonus bug: `softImpute::complete()` returns `np.ndarray` directly in R 4.5/rpy2 3.5.5 — added `isinstance` guard (same pattern used elsewhere in the file)

---

### Phase 5 — Code Change: `run_cross_product_parallel.py`
*Modifies: `run_cross_product_parallel.py`*

- [x] **5.1** Added `import os` at imports block
- [x] **5.2** Added `_POD_NAME` and `_S3_FAILED_PREFIX` constants after `FAILED_LOG_PATH`
- [x] **5.3** Implemented `_sync_failed_log_from_s3()` with `list_objects_v2` pagination over `{S3_PREFIX}/failed_jobs_` prefix — reads all pods' files
- [x] **5.4** Implemented `_sync_failed_log_to_s3()` writing to `failed_jobs_{POD_NAME}.txt`; deletes object on clean run
- [x] **5.5** Wired `_sync_failed_log_from_s3()` into `main()` before `_load_failed_log()`
- [x] **5.6** Wired `_sync_failed_log_to_s3(updated_failed)` into `main()` after `_save_failed_log()`
- [x] **5.7** S3 list confirmed working (0 failed keys currently — empty prefix, no error)

---

### Phase 6 — Mock Test Script
*Produces: `harmonization-scripts/test_mock.py`*

- [x] **6.1** Created `test_mock.py`
- [x] **6.2** Ran locally: all 24 normalization methods + 4 imputation methods tested
- [x] **6.3** Two failures found and fixed: (1) `softimpute` — rpy2 numpy conversion bug in `bench_shared.py`; (2) `23_vst` — synthetic data rounds to zeros, fixed by +2.0 offset in test data. Final result: 22 PASS, 2 SKIP (shambhala/PEER — both expected)
- [x] **6.4** Full tracebacks print under `FAILURE DETAILS` section ✓
- [x] **6.5** Exit code 0 on clean run confirmed ✓

---

### Phase 7 — Docker Build (Local)
*Produces: local image `fl-batch-correction:latest`*

- [ ] **7.1** Run the build from the project root:
  ```bash
  cd ~/B_cell_lymphomas
  docker build --tag fl-batch-correction:latest --file harmonization-scripts/Dockerfile .
  ```
- [ ] **7.2** Monitor the R package installation layer — the most likely failure points are:
  - Missing system library for a Bioconductor package (add to `apt-get install` in the Dockerfile)
  - `TDM` or `HarmonizR` GitHub install fails (network timeout or API change) — if so, add a `wget` pre-download step
  - `warn = 2` treating a warning as an error — relax to `warn = 1` in `install_r_packages.R`
- [ ] **7.3** Monitor the Python package installation layer:
  - If `scanorama` fails to build from source, add `build-essential` (already in Dockerfile ✓) or find a wheel
  - If `rpy2` fails, verify R headers are present (`r-base-dev` ✓)
- [ ] **7.4** Record the final image size (`docker images fl-batch-correction`) — expect 3–6 GB
- [ ] **7.5** Verify rpy2 can reach R inside the image:
  ```bash
  docker run --rm fl-batch-correction:latest python -c \
      "import rpy2.robjects as ro; print(ro.r('R.version.string')[0])"
  ```
- [ ] **7.6** Verify all expected R packages load without error:
  ```bash
  docker run --rm fl-batch-correction:latest Rscript -e \
      "for (p in c('limma','sva','RUVSeq','batchelor','qsmooth','edgeR','DESeq2','FSQN','TDM','HarmonizR','missForest','softImpute')) { library(p, character.only=TRUE); cat(p, 'OK\n') }"
  ```

---

### Phase 8 — Docker Smoke Test
*Validates the full image before pushing to ECR*

- [ ] **8.1** Run `test_mock.py` inside the container (with AWS credentials mounted):
  ```bash
  docker run --rm \
      -v "$HOME/.aws:/root/.aws:ro" \
      fl-batch-correction:latest \
      python test_mock.py
  ```
- [ ] **8.2** Confirm exit code 0 and that all methods are `PASS` or expected `SKIP`
- [ ] **8.3** Confirm the `sleep infinity` default keeps the container alive when no command is given:
  ```bash
  docker run -d --name test-idle fl-batch-correction:latest
  sleep 5 && docker ps | grep test-idle   # should still be running
  docker rm -f test-idle
  ```
- [ ] **8.4** Confirm `kubectl exec`-style script execution works (using `docker exec` as a proxy):
  ```bash
  docker run -d --name test-exec \
      -v "$HOME/.aws:/root/.aws:ro" \
      fl-batch-correction:latest
  docker exec test-exec python run_one_job.py \
      --strat A_confirmed_bad --imp strict --method 01_raw \
      --skip-if-exists --out-json /tmp/test.json
  docker exec test-exec cat /tmp/test.json
  docker rm -f test-exec
  ```

---

### Phase 9 — AWS Infrastructure Setup
*One-time setup; skip if already done*

- [x] **9.1** Account ID: `${AWS_ACCOUNT_ID}`, region: `us-east-1`, ECR URI: `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction`
- [ ] **9.2** Create the ECR repository — **requires `ecr:CreateRepository` permission (admin action)**:
  ```bash
  aws ecr create-repository --repository-name fl-batch-correction --region us-east-1
  ```
- [ ] **9.3** Confirm Karpenter node IAM role includes ECR pull permissions — **check with infra team**
- [ ] **9.4** Create the K8s credentials Secret — **run on local machine with kubectl**:
  ```bash
  kubectl create secret generic aws-credentials \
      --from-file=credentials=$HOME/.aws/credentials \
      --from-file=config=$HOME/.aws/config \
      --namespace ${K8S_NAMESPACE}
  ```
- [ ] **9.5** Verify the Secret exists: `kubectl get secret aws-credentials -n ${K8S_NAMESPACE}`

---

### Phase 10 — Push Image to ECR

- [ ] **10.1** Authenticate Docker to ECR:
  ```bash
  aws ecr get-login-password --region "$AWS_REGION" \
      | docker login --username AWS --password-stdin "$ECR_URI"
  ```
- [ ] **10.2** Tag and push `latest` plus a dated version tag (Step 10.1):
  ```bash
  VERSION=$(date +%Y%m%d)
  docker tag fl-batch-correction:latest "${ECR_URI}:latest"
  docker tag fl-batch-correction:latest "${ECR_URI}:${VERSION}"
  docker push "${ECR_URI}:latest"
  docker push "${ECR_URI}:${VERSION}"
  ```
- [ ] **10.3** Confirm the push succeeded:
  ```bash
  aws ecr describe-images --repository-name fl-batch-correction --region "$AWS_REGION"
  ```

---

### Phase 11 — Kubernetes Manifests

- [x] **11.1** Created `harmonization-scripts/k8s/` directory
- [x] **11.2** Created `k8s/pod.yaml`; ECR URI pre-filled as `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest`
- [x] **11.3** Created `k8s/aws-credentials-secret.yaml` (reference-only, instructions in file header)
- [ ] **11.4** Validate pod YAML syntax — **run on local machine with kubectl**: `kubectl apply --dry-run=client -f k8s/pod.yaml`

---

### Phase 12 — End-to-End Validation in the Pod

- [ ] **12.1** Confirm input data is uploaded to S3 at the exact keys from task 0.6:
  ```bash
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/
  ```
- [ ] **12.2** Apply the pod: `kubectl apply -f harmonization-scripts/k8s/pod.yaml`
- [ ] **12.3** Wait for the pod to reach `Running` state: `kubectl get pod fl-batch-correction -n ${K8S_NAMESPACE} -w`
- [ ] **12.4** Attach via VSCode Kubernetes extension or `kubectl exec`:
  ```bash
  kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash
  ```
- [ ] **12.5** Inside the pod, confirm AWS credentials work:
  ```bash
  aws sts get-caller-identity
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/
  ```
- [ ] **12.6** Inside the pod, run the smoke test: `python test_mock.py`
- [ ] **12.7** Inside the pod, run one real job as a minimal end-to-end check:
  ```bash
  python run_one_job.py \
      --strat A_confirmed_bad --imp strict --method 01_raw \
      --out-json /tmp/check.json
  cat /tmp/check.json   # expect status "ok"
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/ | grep 01_raw
  ```
- [ ] **12.8** Verify the S3 data download and pickle cache work: confirm `/tmp/bench_comb_data.pkl` exists after the job and that a second job call is faster (cache hit)
- [ ] **12.9** Run a small dispatcher subset to test multi-worker mode:
  ```bash
  python run_cross_product_parallel.py \
      --strats A_confirmed_bad --imps strict \
      --methods 01_raw,17_quantile,16_fsqn_r \
      --n-workers 2 --skip-if-exists
  ```
- [ ] **12.10** Confirm `failed_jobs_{POD_NAME}.txt` appears in S3:
  ```bash
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/ | grep failed_jobs
  ```
- [ ] **12.11** Confirm `metrics.csv` was uploaded:
  ```bash
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/metrics.csv
  ```

---

### Phase 13 — Multi-Pod Parallel Run (optional, after Phase 12 is green)

- [ ] **13.1** Plan the job grid split — example: pod-1 takes strategies `S0,A,B,C,D`; pod-2 takes `E1,E2,E3,F,G`
- [ ] **13.2** Create a second pod YAML (`k8s/pod-2.yaml`) with a different `metadata.name` and `command`/`args` pointing to the correct `--strats` subset
- [ ] **13.3** Apply both pods simultaneously; verify they do not duplicate work (each pod's S3 expression keys are non-overlapping by strategy)
- [ ] **13.4** After both pods complete, verify that a new pod reading S3 failed-jobs sees the union of failures from both runs:
  ```bash
  aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/ | grep failed_jobs
  # expect two files: one per pod
  ```
- [ ] **13.5** Load final merged metrics in the notebook and confirm row counts match expectations

---

### Phase 14 — Housekeeping

- [ ] **14.1** Add `.dockerignore` at the project root (task 3.2) if not already done
- [ ] **14.2** Update the `## 13. Implementation Checklist` in this document as phases complete
- [ ] **14.3** Commit all new files (`requirements.txt`, `install_r_packages.R`, `Dockerfile`, `test_mock.py`, `k8s/pod.yaml`, `k8s/aws-credentials-secret.yaml`, `.dockerignore`) to git — **do not commit** `~/.aws/credentials` or any `.pkl` / `.tsv` data files
- [ ] **14.4** Tag the Docker image with the git commit SHA for full reproducibility:
  ```bash
  GIT_SHA=$(git -C ~/B_cell_lymphomas rev-parse --short HEAD)
  docker tag fl-batch-correction:latest "${ECR_URI}:${GIT_SHA}"
  docker push "${ECR_URI}:${GIT_SHA}"
  ```
