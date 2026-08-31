# Skill: docker-image

Complete reference for the Docker image, Kubernetes deployment, and related infrastructure files.

---

## Image Summary

| Attribute | Value |
|---|---|
| Base | `python:3.11-slim` (Debian 12 / bookworm) |
| Python | 3.11 |
| R | 4.5.3 (from CRAN `bookworm-cran40` apt repo) |
| Bioconductor | 3.22 |
| ECR URI | `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction` |
| WORKDIR | `/app/harmonization-scripts` |
| Default CMD | `["sleep", "infinity"]` (pod stays alive for interactive use) |

---

## Files

### `Dockerfile`

```
FROM python:3.11-slim

# 1. System libs: build tools, R prerequisites, image/compression headers
RUN apt-get install gnupg2 ca-certificates wget curl git
    build-essential gfortran
    libcurl4-openssl-dev libssl-dev libxml2-dev
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev
    libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev
    libhdf5-dev libbz2-dev liblzma-dev zlib1g-dev

# 2. R 4.5 via CRAN apt repo
# CRAN repo: bookworm-cran40  (ships R 4.5.x despite "40" in name)
# GPG key fingerprint: 95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7
RUN apt-get install r-base r-base-dev

# 3. R packages (CRAN + Bioconductor + GitHub)
COPY harmonization-scripts/install_r_packages.R /tmp/
RUN Rscript /tmp/install_r_packages.R

# 4. Python packages
COPY harmonization-scripts/requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 5. Scripts
WORKDIR /app
COPY harmonization-scripts/ harmonization-scripts/
WORKDIR /app/harmonization-scripts

CMD ["sleep", "infinity"]
```

**Key detail:** `WORKDIR /app/harmonization-scripts` must match `cwd=str(Path(__file__).parent)` in `run_cross_product_parallel.py`'s subprocess call, so that `run_one_job.py` is found without a path prefix and `from bench_shared import ...` resolves correctly.

### `requirements.txt`

```
boto3>=1.28.17
botocore>=1.31.17
pandas>=2.0
numpy>=1.24
scikit-learn>=1.3
rpy2>=3.5.5
harmonypy>=0.0.9
scanorama>=1.7
combat>=0.3.3
inmoose>=0.9.1
psutil>=5.9
```

Note: `matplotlib`, `seaborn`, `jupyter` are intentionally excluded (not used by the benchmark scripts).

### `install_r_packages.R`

Installs all required R packages inside the Docker image. Verified locally with R 4.5.3 and Bioconductor 3.22. Exit code non-zero if any package is missing after install.

**CRAN packages:** `missForest`, `softImpute`, `FSQN`, `remotes`

**Bioconductor packages:** `limma`, `sva`, `RUVSeq`, `batchelor`, `qsmooth`, `edgeR`, `DESeq2`

**GitHub packages:**
- `greenelab/TDM` — Training Distribution Matching (Thompson et al. 2016)
- `HSU-HPC/HarmonizR` — NA-aware ComBat/limma wrapper (Voss et al. 2022)

Verified installed package versions: limma 3.66, sva 3.58, RUVSeq 1.44, batchelor 1.26, qsmooth 1.26, edgeR 4.8, DESeq2 1.50, missForest 1.6, softImpute 1.4, FSQN 0.0.1, TDM 0.3, HarmonizR 0.99.2.

---

## Build and Push Workflow

Run from the **project root** (`~/B_cell_lymphomas/`):

```bash
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction"
AWS_REGION="us-east-1"

# 1. Build (20–40 min; R Bioconductor layer is the slowest)
docker build \
    --tag fl-batch-correction:latest \
    --file harmonization-scripts/Dockerfile \
    .

# 2. Verify rpy2 reaches R inside the image
docker run --rm fl-batch-correction:latest python -c \
    "import rpy2.robjects as ro; print(ro.r('R.version.string')[0])"

# 3. Smoke test (requires AWS credentials for S3 write in some methods)
docker run --rm \
    -v "$HOME/.aws:/root/.aws:ro" \
    fl-batch-correction:latest \
    python test_mock.py

# 4. Log in to ECR
aws ecr get-login-password --region "$AWS_REGION" \
    | docker login --username AWS --password-stdin "$ECR_URI"

# 5. Tag and push
VERSION=$(date +%Y%m%d)
docker tag fl-batch-correction:latest "${ECR_URI}:latest"
docker tag fl-batch-correction:latest "${ECR_URI}:${VERSION}"
docker push "${ECR_URI}:latest"
docker push "${ECR_URI}:${VERSION}"

# 6. Confirm push
aws ecr describe-images --repository-name fl-batch-correction --region "$AWS_REGION"
```

### Rebuild tips
- Use `--cache-from "${ECR_URI}:latest"` to reuse the R layer and skip the 20–40 min install on reruns
- If TDM/HarmonizR GitHub install fails (network), pre-download tarballs with `wget` and `COPY` them
- Expected final image size: 3–6 GB

---

## Kubernetes Manifests

### `k8s/pod.yaml`

Main pod spec. Key fields:

| Field | Value |
|---|---|
| `metadata.name` | `fl-batch-correction` |
| `metadata.namespace` | `${K8S_NAMESPACE}` |
| `spec.restartPolicy` | `Never` |
| `image` | `${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/fl-batch-correction:latest` |
| `resources` | 8 CPU / 16 GiB (request = limit) |
| `nodeSelector` | `karpenter.k8s.aws/instance-family: c6a` |
| Toleration | `node-group=${K8S_NAMESPACE} NoSchedule` |
| Volume mounts | `/workspace` (PVC) + `/root/.aws` (Secret, readOnly) |

**Env vars:**
- `POD_NAME` — injected from `metadata.name`; used as the per-pod S3 failed-jobs key suffix
- `BENCH_EXP_S3_KEY` / `BENCH_ANN_S3_KEY` — optional overrides for S3 input paths (commented out by default)

**Unattended batch run:** uncomment `command`/`args` in the pod spec:
```yaml
command: ["python", "run_cross_product_parallel.py"]
args:
  - "--n-workers"
  - "6"
  - "--skip-if-exists"
  - "--memory-limit-gb"
  - "12.0"
  - "--timeout-s"
  - "3600"
```

### `k8s/aws-credentials-secret.yaml`

Reference file only — shows the Secret structure. Create the actual Secret with:

```bash
kubectl create secret generic aws-credentials \
    --from-file=credentials=$HOME/.aws/credentials \
    --from-file=config=$HOME/.aws/config \
    --namespace ${K8S_NAMESPACE}

kubectl get secret aws-credentials -n ${K8S_NAMESPACE}
```

### `create_pvc.yaml`

100 GiB PVC `fl-workspace` (ReadWriteOnce) mounted at `/workspace` inside the pod.

```bash
kubectl apply -f harmonization-scripts/create_pvc.yaml
```

### `c6a.2xlarge-pod.yaml`

Legacy manifest using `python:3.11` (plain, no custom image). Kept for reference.

---

## Pod Lifecycle

```bash
# Apply pod
kubectl apply -f harmonization-scripts/k8s/pod.yaml

# Watch status
kubectl get pod fl-batch-correction -n ${K8S_NAMESPACE} -w

# Stream logs
kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}

# Attach (interactive)
kubectl exec -it fl-batch-correction -n ${K8S_NAMESPACE} -- bash

# Delete pod (after run completes)
kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
```

Inside the pod, the working directory is `/app/harmonization-scripts`. The pickle caches go to `/tmp/` (lost when pod is deleted). For persistent caches across pod restarts, write to `/workspace/` (PVC).

---

## S3 Input Data Upload (one-time)

```bash
aws s3 cp comb_exp.tsv \
    s3://$FL_S3_BUCKET/FL_batch_correction/exp/comb_exp.tsv

aws s3 cp comb_ann_unified.csv \
    s3://$FL_S3_BUCKET/FL_batch_correction/exp/comb_ann_unified.csv

# Verify
aws s3 ls s3://$FL_S3_BUCKET/FL_batch_correction/exp/
```

Confirmed S3 keys (uncompressed):
- `FL_batch_correction/exp/comb_exp.tsv` (1.9 GB)
- `FL_batch_correction/exp/comb_ann_unified.csv` (6.9 MB)

---

## Multi-Pod Parallel Runs

To split the 960-job grid across multiple pods:

1. Create additional pod YAMLs with unique `metadata.name` values
2. Pass non-overlapping `--strats` or `--methods` subsets via `args:`
3. Each pod writes its own `failed_jobs_{POD_NAME}.txt` to S3 — no write conflicts
4. On startup, every pod merges all pods' failed-job files from S3 automatically

Example split: pod-1 handles `S0,A,B,C,D`; pod-2 handles `E1,E2,E3,F,G`.

---

## Known Issues and Mitigations

| Issue | Mitigation |
|---|---|
| R build takes 20–40 min | Use `--cache-from` to reuse the R layer on rebuilds |
| TDM/HarmonizR GitHub repos unavailable | Pre-download tarballs; `COPY` + `install.packages(path)` |
| `comb_exp.tsv` 1.9 GB S3 download | Pickle cache at `/tmp/bench_comb_data.pkl` handles it after first download per pod |
| S3_EXP_KEY default may not match actual key | Confirm with `aws s3 ls …/exp/`; override via `BENCH_EXP_S3_KEY` env var |
| `softImpute::complete()` returns numpy array in R 4.5 / rpy2 3.5.5 | Fixed with `isinstance(imp_mat, np.ndarray)` guard in `bench_shared.py` |
| ECR repo creation needs admin | Request `ecr:CreateRepository` from infra team |
