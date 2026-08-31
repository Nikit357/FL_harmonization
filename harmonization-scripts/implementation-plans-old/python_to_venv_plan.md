# Implementation Plan: Python Virtual Environment for the K8s Pod

## Root Cause Analysis

From the pod logs, there are **four distinct bugs** — not one:

### Bug 1: `git` not in the apt-get install list
Step 2 of the startup script installs system libraries but does NOT include `git`. As a result, the `git clone https://github.com/BostonGene/Procrustes.git /app/Procrustes` command in step 5 silently fails (the `&&` means the echo is skipped, but the script continues). The pod appears healthy but Procrustes is never cloned.

### Bug 2: `requirements.txt` has an uninstallable Procrustes entry
`requirements.txt` line 13: `procrustes-bg @ git+https://github.com/BostonGene/Procrustes`

Procrustes has no `setup.py` or `pyproject.toml`, so `pip install` of this entry always fails with:
> `does not appear to be a Python project`

This is redundant anyway: `bench_shared.py:2617–2619` already handles Procrustes by inserting `/app/Procrustes` into `sys.path` at call time. The pip entry should be removed.

### Bug 3: `reComBat` missing from `requirements.txt`
`bench_shared.py:2026` does `from reComBat import reComBat as _ReComBat`. The ConfigMap in `pod-ssh.yaml` correctly lists `reComBat>=0.3`, but the repo's `requirements.txt` does not. These are out of sync. Any fresh install from the repo file will fail for method `30_recombat`.

### Bug 4: `--break-system-packages` is fragile on Ubuntu 24.04
Ubuntu 24.04 enforces PEP 668: pip refuses to install into the system Python without `--break-system-packages`. The flag works, but it is explicitly discouraged and brittle — future apt upgrades can overwrite or conflict with pip-installed packages. A virtual environment is the correct fix and also eliminates the need for the flag entirely.

---

## Proposed Solution

Create a Python virtual environment at `/app/venv` during pod startup. All Python packages are installed into the venv. The venv is activated in `.bashrc` and `.profile` so it is active in every SSH/exec session automatically.

---

## Files to Change

### 1. `requirements.txt`
- Remove `procrustes-bg @ git+https://github.com/BostonGene/Procrustes` (uninstallable; bench_shared.py handles it via sys.path)
- Add `reComBat>=0.3` (used in `normalize_recombat`; currently only in the ConfigMap)

### 2. `k8s/pod-ssh.yaml` — startup script (step 2)
- Add `git python3-venv python3-full` to the apt-get install line

### 3. `k8s/pod-ssh.yaml` — startup script (new step 2.5, after system libs)
Create the venv and activate it for the remainder of the startup script:
```bash
python3 -m venv /app/venv
source /app/venv/bin/activate
echo 'source /app/venv/bin/activate' >> /root/.bashrc
echo 'source /app/venv/bin/activate' >> /root/.profile
```

### 4. `k8s/pod-ssh.yaml` — startup script (step 4, Python packages)
Change:
```bash
pip3 install --break-system-packages --no-cache-dir -r /etc/fl-deps/requirements.txt
```
To:
```bash
/app/venv/bin/pip install --no-cache-dir -r /etc/fl-deps/requirements.txt
```
(The venv pip does not need `--break-system-packages`.)

### 5. `k8s/pod-ssh.yaml` — ConfigMap `fl-deps` (requirements.txt block)
Sync the ConfigMap with the repo `requirements.txt`:
- Remove `reComBat>=0.3` is fine to keep (it IS needed)
- Do NOT add `procrustes-bg` (handled by git clone)
- Ensure all other packages match `requirements.txt`

### 6. `k8s/README.md`
- Add a note that after SSH-ing in, the venv is activated automatically via `.bashrc`
- Update all `python`/`pip` command examples to make clear that `python` inside the pod means the venv Python
- Add a troubleshooting entry: `ModuleNotFoundError` → "venv may not be active; run `source /app/venv/bin/activate`"
- Update the "Manually installing missing Python packages" section to use `/app/venv/bin/pip install`

---

## Step-by-step Changes

### `requirements.txt` — diff

```diff
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
 awscli>=1.29
-procrustes-bg @ git+https://github.com/BostonGene/Procrustes
+reComBat>=0.3
```

### `k8s/pod-ssh.yaml` — step 2 apt-get line

```diff
-        apt-get install -y -qq build-essential gfortran cmake ... python3 python3-pip python3-dev python-is-python3 software-properties-common octave octave-statistics
+        apt-get install -y -qq build-essential gfortran cmake ... python3 python3-pip python3-dev python3-venv python3-full python-is-python3 git software-properties-common octave octave-statistics
```

### `k8s/pod-ssh.yaml` — insert venv creation block after step 2 echo

```bash
        # -- 2.5. Python virtual environment --
        python3 -m venv /app/venv
        source /app/venv/bin/activate
        echo 'source /app/venv/bin/activate' >> /root/.bashrc
        echo 'source /app/venv/bin/activate' >> /root/.profile
        echo "[startup] Python venv created at /app/venv"
```

### `k8s/pod-ssh.yaml` — step 4 pip install

```diff
-        pip3 install --break-system-packages --no-cache-dir -r /etc/fl-deps/requirements.txt
+        /app/venv/bin/pip install --no-cache-dir -r /etc/fl-deps/requirements.txt
```

### `k8s/pod-ssh.yaml` — ConfigMap `fl-deps` requirements.txt block

```diff
     requirements.txt: |
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
       awscli>=1.29
       reComBat>=0.3
-      # (procrustes-bg is NOT listed here — installed by git clone + sys.path in bench_shared.py)
```
Note: the ConfigMap already had `reComBat>=0.3`, so this block is already correct. The only real sync needed is removing `procrustes-bg` if it was ever added.

---

## Does This Solve All Problems?

| Problem | Fix | Solved? |
|---|---|---|
| `git` not installed → Procrustes clone fails | Added `git` to step 2 apt-get | ✅ |
| `procrustes-bg` pip entry fails (no setup.py) | Removed from requirements.txt | ✅ |
| `reComBat` missing from requirements.txt | Added `reComBat>=0.3` | ✅ |
| `--break-system-packages` fragility | Replaced with venv pip install | ✅ |
| `ModuleNotFoundError` for numpy/pandas | Venv created before step 4; sourced in .bashrc so every session has it | ✅ |
| User connects before packages are ready | Venv creation is part of the fast init (~2 min along with SSH). Packages install during step 4. README warns not to run scripts until `[startup] Environment ready.` appears | ✅ (same as before — timing is unchanged) |

### One remaining caveat
If the user connects via `kubectl exec -it ... -- bash` (non-login, non-interactive shell), `.bashrc` may not be sourced automatically. The fix is to either:
- Use `kubectl exec -it ... -- bash -l` (login shell, sources `.profile`)
- Or simply run `source /app/venv/bin/activate` manually once

This is a minor usability issue, not a blocking one. It will be documented in the README troubleshooting table.

---

## Procrustes: Why the Current Approach Is Correct

`bench_shared.py` normalizes Procrustes at call time via:
```python
_PROCRUSTES_PATH = "/app/Procrustes"
if _PROCRUSTES_PATH not in sys.path:
    sys.path.insert(0, _PROCRUSTES_PATH)
```

This is intentional because Procrustes has no packaging metadata (`setup.py`/`pyproject.toml`). The git clone at startup puts the module directory at `/app/Procrustes`, and `bench_shared.py` adds it to `sys.path` on first use. This pattern is already correct and does not need to change.

After the fix, the startup sequence becomes:
1. Git is installed (step 2) → clone succeeds (step 5) → `/app/Procrustes` exists
2. `sys.path.insert` in `bench_shared.py` → import succeeds

---

## Order of Implementation

1. ✅ Edit `requirements.txt` (remove procrustes-bg, add reComBat)
2. ✅ Edit `k8s/pod-ssh.yaml` (git + python3-venv in step 2, new venv block, step 4 pip change)
3. ✅ Edit `k8s/README.md` (venv activation note + troubleshooting update)
4. Delete the old pod and re-apply the manifest to test:
   ```bash
   kubectl delete pod fl-batch-correction -n ${K8S_NAMESPACE}
   kubectl apply -f harmonization-scripts/k8s/pod-ssh.yaml -n ${K8S_NAMESPACE}
   kubectl logs -f fl-batch-correction -n ${K8S_NAMESPACE}
   # Wait for: [startup] Environment ready.
   ssh fl-pod
   python test_mock.py
   ```
