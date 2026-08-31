# Deviation from Original GitHub: Local Shambhala2 vs. BorisovNM/Shambhala2

**Date:** 2026-05-14  
**Compared:** local `/shambhala_adoption/Shambhala2/` vs. https://github.com/BorisovNM/Shambhala2 (master branch)  
**Context:** See `Shambhala_research_260513.md` for background on Shambhala2 algorithm and its application to the FL project.

---

## Summary Table

| File | Status | Algorithmic Change? |
|---|---|---|
| `Shambhala2.m` | Modified (cosmetic) | No |
| `CuBlock.m` | Modified (compatibility rewrites) | Minor (see §3) |
| `readExpressionData.m` | Modified (cosmetic) | No |
| `Shambhala2.R` | Modified + extended | No to core algorithm; substantial extension |
| `quantilenorm.m` | **New file (not in GitHub)** | Replaces MATLAB toolbox function |
| `kmeans.m` | **New file (not in GitHub)** | Replaces MATLAB/Octave stats package |

---

## 1. `Shambhala2.m` — Cosmetic Change Only

### Difference

**GitHub (line 44):**
```matlab
outFileName = append("Cu_bis.txt");
```

**Local (line 44):**
```matlab
outFileName = 'Cu_bis.txt';
```

### Assessment

`append("Cu_bis.txt")` with a single string argument simply returns the same string unchanged. Both expressions assign the identical string `'Cu_bis.txt'` to `outFileName`. The rest of the file is character-for-character identical (whitespace notwithstanding).

**Algorithmic impact: None.** The `append()` call was apparently removed to improve clarity and avoid an unnecessary function call. The data flow, the loop structure, the quantilenorm/CuBlock call order, and the output format are all unchanged.

---

## 2. `readExpressionData.m` — Cosmetic Change Only

### Difference

**GitHub (inside the loop over columns):**
```matlab
strDataFormat=strcat(strDataFormat,'%f64');
```

**Local:**
```matlab
strDataFormat = [strDataFormat, '%f64'];
```

### Assessment

In MATLAB/Octave, string concatenation via `[a, b]` and via `strcat(a, b)` produce identical results for non-padded strings. This is a style preference. All other lines in the file are identical.

**Algorithmic impact: None.** File parsing, log2 transformation, and struct output are unchanged.

---

## 3. `CuBlock.m` — Compatibility Rewrites (Mostly Equivalent, One Nuance)

This is the most extensively modified file. The GitHub version relies on three MATLAB/Octave toolbox functions not available in the Conda Octave installation: `std(...,'omitnan')`, `mean(...,'omitnan')`, `polyfit`, and `polyval`. All four have been replaced with primitive Octave operations.

### 3a. Mean and standard deviation (`std` / `mean` with `'omitnan'`)

**GitHub:**
```matlab
dataCurrStd = std(dataCurr,'omitnan');
if dataCurrStd>0
    dataCurr = (dataCurr - mean(dataCurr,'omitnan'))/dataCurrStd;   % Z-transform
```

**Local:**
```matlab
valid_mask = ~isnan(dataCurr);
valid_data = dataCurr(valid_mask);
n_valid = sum(valid_mask);

if n_valid > 1
    curr_mean = sum(valid_data) / n_valid;
    dataCurrStd = sqrt(sum((valid_data - curr_mean).^2) / (n_valid - 1));
else
    if n_valid == 1
        curr_mean = valid_data(1);
    else
        curr_mean = 0;
    end
    dataCurrStd = 0;
end
% ...
dataCurr = (dataCurr - curr_mean)/dataCurrStd;   % Z-transform
```

**Assessment:** The local version manually reimplements the sample standard deviation (n−1 denominator), which is exactly what `std(...,'omitnan')` computes. The `'omitnan'` flag is only needed defensively — the CuBlock docstring explicitly states "The micro array cannot contain NaN values," so in practice both paths operate on the same data. Edge cases (n_valid = 0 or 1) in the local version produce `dataCurrStd = 0`, which is also what `std` of a constant or empty vector returns, and the downstream `if dataCurrStd>0` guard correctly skips these blocks in both versions.

**Algorithmic impact: None under normal data.** The result is mathematically identical for NaN-free input. The local version adds more explicit edge-case handling that the original skips because it assumes clean input.

---

### 3b. Column mean in GetTargetValues

**GitHub:**
```matlab
S = mean(abs(X(indStdDown:indStdUp,:)));
```

**Local:**
```matlab
X_subset = abs(X(indStdDown:indStdUp,:));
S = sum(X_subset, 1) / size(X_subset, 1);
```

**Assessment:** `mean(M)` without a dimension argument computes column-wise means by default in both MATLAB and Octave. `sum(M, 1) / size(M, 1)` is the explicit equivalent. Results are bit-for-bit identical.

**Algorithmic impact: None.**

---

### 3c. Polynomial fitting (`polyfit` → Vandermonde `\`)

**GitHub:**
```matlab
pol = polyfit(dataCurrS, X(:,indP), 3);
```

**Local:**
```matlab
V = [dataCurrS.^3, dataCurrS.^2, dataCurrS, ones(size(dataCurrS))];
pol = V \ X(:,indP);
```

**Assessment:** Both approaches solve the same overdetermined least-squares problem: find coefficients [a₃, a₂, a₁, a₀] that minimize ‖V·pol − X(:,indP)‖². `polyfit(x, y, 3)` constructs exactly this Vandermonde matrix internally and solves by QR decomposition; `V \ X` in Octave also uses QR/pseudoinverse for overdetermined systems. The mathematical problem is identical.

The practical difference is numerical stability. MATLAB's `polyfit` documentation states that it normalizes x internally to `(x − μ)/σ` for better conditioning. The Vandermonde `\` approach does not do this. For gene expression data that has already been Z-transformed by the preceding step (mean ≈ 0, std ≈ 1), x values are bounded roughly in [−3, 3], so the Vandermonde matrix is well-conditioned and the numerical difference is negligible.

**Algorithmic impact: Negligible in practice.** For the Z-score-scaled gene expression input that CuBlock receives, conditioning is not an issue. Results may differ in the last few floating-point digits compared to `polyfit`, but not in any biologically meaningful way. If the input were not Z-transformed (violating CuBlock's assumptions), this choice could matter more.

---

### 3d. Polynomial evaluation (`polyval` → explicit formula)

**GitHub (in `ModPol`):**
```matlab
dataNS = polyval(pol, data(indS));
```

**Local:**
```matlab
x_val = data(indS);
dataNS = pol(1)*(x_val.^3) + pol(2)*(x_val.^2) + pol(3)*x_val + pol(4);
```

**Assessment:** `polyval([a₃,a₂,a₁,a₀], x)` evaluates a₃x³ + a₂x² + a₁x + a₀, which is precisely what the explicit formula computes. `polyval` uses Horner's method (slightly more numerically stable), but for a cubic polynomial on bounded inputs the difference is at floating-point noise level.

Note: since `pol` coefficients are produced by the Vandermonde method described in §3c rather than `polyfit`, there is a consistent treatment: the same coefficient format ([a₃,a₂,a₁,a₀]) is used by both the fitting step and the evaluation step in the local version. This is internally consistent.

**Algorithmic impact: None.**

---

## 4. `Shambhala2.R` — MATLAB→Octave, New `Shambhala2_flex`, Added Diagnostics

### 4a. Runtime engine: MATLAB replaced with Octave

**GitHub:**
```r
system("matlab -nodesktop -nosplash -nodisplay -r \"run('Shambhala2.m');exit;\"")
```

**Local:**
```r
octave_cmd = "/opt/conda/bin/octave --no-gui --eval \"source('Shambhala2.m');\" > octave_debug.log 2>&1"
system(octave_cmd)
```

**Assessment:** The engine swap from MATLAB to Octave is the reason for all the `.m` script changes described in §1–3. The intermediate file protocol (args.txt, P_prim.txt, Cu_bis.txt) is preserved identically. The log is redirected to `octave_debug.log` for debugging. Output is captured to a log file rather than stdout, which is a useful operational improvement. The computational result produced by Octave with the custom `quantilenorm.m` and `kmeans.m` (see §5–6) should match the MATLAB result to within floating-point noise.

**Algorithmic impact: None** (given that the Octave custom implementations are correct — see §5 and §6).

---

### 4b. Added `Shambhala2_flex` function

The local `Shambhala2.R` adds a second function, `Shambhala2_flex(InputDataFrame, PFileName, QFileName, ...)`, which is absent from the GitHub version. It accepts a pre-loaded R data.frame as input instead of a file path. This is the entry point called from the Python benchmark pipeline via `rpy2`.

The internal logic of `Shambhala2_flex` is algorithmically identical to `Shambhala2`: merge → write P_prim.txt + args.txt → run Octave → read Cu_bis.txt → Q-rescale. Two implementation differences relative to the local `Shambhala2`:

1. `read.table(Cu2FN, header = FALSE, sep = " ")` — explicit space separator. The local `Shambhala2` uses `read.table(Cu2FN, header = FALSE)` (default whitespace). These are functionally equivalent since R's default white-space delimiter correctly parses space-separated files.
2. The variable holding the Octave output is renamed from `MAS` to `MAS_out` to reduce ambiguity with the input `MAS`. No functional effect.

**Algorithmic impact: None.** `Shambhala2_flex` is a new access layer, not an algorithmic change.

---

### 4c. Added diagnostic output and error checking in `Shambhala2`

The local `Shambhala2` function adds `cat(...)` statements printing dimensions at each step and a guard:
```r
if (!file.exists(Cu2FN)) {
    stop("🛑 OCTAVE EXECUTION FAILED! Cu_bis.txt was not generated.")
}
```

**Algorithmic impact: None.** These are operational improvements (debuggability, fail-fast behavior).

---

### 4d. Changed default run targets

**GitHub:**
```r
Harmonized = Shambhala2("Input.csv", "P0.csv", "Q0.csv", ...)
OFN = "Output.csv"
```

**Local:**
```r
Harmonized = Shambhala2("comb_exp_log_dedup.csv", "P0.csv", "Q0.csv", ...)
OFN = "shambhala_harmonized.csv"
```

**Assessment:** The top-level execution block has been adapted to run on the full FL dissertation dataset rather than the toy example. `Shambhala2_flex` and its use from the Python pipeline bypass this block entirely.

**Algorithmic impact: None.**

---

## 5. `quantilenorm.m` — New File (Not in GitHub Repository)

The GitHub repository **does not include** a `quantilenorm.m` file. It requires the MATLAB Bioinformatics Toolbox function `quantilenorm`, which is not available in the Conda Octave installation used by this project.

### Local implementation:
```matlab
function norm_data = quantilenorm(data)
    [sorted_data, original_indices] = sort(data, 1);
    num_samples = size(sorted_data, 2);
    rank_means = sum(sorted_data, 2) / num_samples;
    norm_data = zeros(size(data));
    for i = 1:num_samples
        norm_data(original_indices(:, i), i) = rank_means;
    end
end
```

### Assessment

This is the standard quantile normalization algorithm (Bolstad 2003): sort each column independently, compute the mean of each rank across all columns, then map those rank means back to their original positions. This is what MATLAB's `quantilenorm` does for the default ('uniform') distribution reference.

**One potential difference:** MATLAB's `quantilenorm` may handle tied ranks by averaging the tied positions. The local implementation assigns each probe within a tie the mean of its sorted rank position (all tied probes get the same rank_mean anyway since they sort to adjacent identical-value positions, so they all receive the same rank mean). For gene expression data with continuous values, exact ties are rare, making this a non-issue in practice.

**Algorithmic impact: Equivalent for typical gene expression data.** For exact ties, minor differences in value are possible, but these are negligible in biological analyses.

---

## 6. `kmeans.m` — New File (Not in GitHub Repository)

The GitHub repository **does not include** a `kmeans.m` file. It relies on MATLAB's built-in `kmeans` or the Octave statistics package, neither of which is available in the Conda Octave environment.

### Local implementation:
```matlab
function indProbes = kmeans(data, k, varargin)
    maxiter = 1000;
    [n_probes, n_samples] = size(data);
    [~, r_sort] = sort(rand(n_probes, 1));
    rand_idx = r_sort(1:k);
    centroids = data(rand_idx, :);
    indProbes = zeros(n_probes, 1);
    for iter = 1:maxiter
        % Euclidean distance assignment
        ...
        % Convergence check and centroid update
        ...
    end
end
```

### Assessment: This is the most substantive algorithmic divergence.

**Initialization strategy:**  
The local version uses *pure random initialization* — k centroids are drawn uniformly at random from the data points (using `sort(rand(...))` as a `randperm` substitute). MATLAB's built-in `kmeans` defaults to *k-means++* initialization (as of MATLAB 2012+), which deliberately spreads initial centroids to reduce the probability of poor local minima. When called as `kmeans(data, k, 'maxiter', 1000)` without specifying `'Start'`, MATLAB applies k-means++ by default.

**Practical consequences:**  
Different initialization can produce different cluster assignments for the same data. In CuBlock, these cluster assignments determine which probes (genes) are grouped into a block for the cubic polynomial fitting. Different block membership → different polynomial coefficients → different per-block transformation. However, the CuBlock algorithm repeats the entire process **N = 30 times** and averages the results (`dataN = dataN ./ count`). This averaging substantially reduces sensitivity to any single k-means run. The 30-iteration averaging is specifically designed to make CuBlock robust to the stochastic variability of k-means.

**Convergence criterion:**  
The local version uses `sum(indProbes ~= prev_indProbes) == 0` to detect convergence. This is functionally correct.

**Empty cluster handling:**  
The local version reassigns an empty cluster centroid to a randomly chosen data point (`data(ceil(rand() * n_probes), :)`). MATLAB's kmeans handles this differently (it can use a special reinitialization strategy). Empty clusters are uncommon with k=5 on thousands of gene probes.

**Algorithmic impact: Low-to-moderate.** Individual k-means runs will produce different clusterings than MATLAB's k-means++, potentially biasing toward worse local minima. The 30-iteration averaging in CuBlock substantially attenuates this, but does not eliminate it entirely. For large gene sets and k=5, random initialization generally converges to acceptable solutions in practice. The harmonized output is expected to be close to the MATLAB output but not numerically identical. Benchmark testing on the FL dataset showed the method produces valid harmonization, suggesting this difference is not critical in practice.

---

## Overall Algorithmic Integrity Assessment

| Change | Preserves Algorithm? | Notes |
|---|---|---|
| `append()` → string literal | ✅ Yes | Cosmetic |
| `strcat` → `[...]` | ✅ Yes | Cosmetic |
| `std/mean('omitnan')` → primitives | ✅ Yes | Mathematically identical |
| Column `mean` → `sum/size` | ✅ Yes | Mathematically identical |
| `polyfit` → Vandermonde `\` | ✅ Yes (with caveat) | Identical math; minor FP differences on ill-conditioned input |
| `polyval` → explicit formula | ✅ Yes | Identical math |
| MATLAB → Octave | ✅ Yes | Engine swap; algorithm unchanged |
| `quantilenorm` (new) | ✅ Yes | Standard QN algorithm; equivalent for continuous data |
| `kmeans` (new) | ⚠️ Partial | Same algorithm, different initialization; 30× averaging mitigates |
| `Shambhala2_flex` (new) | ✅ Yes | New access layer; not an algorithm change |
| Diagnostic output + error check | ✅ Yes | Operational improvement only |

**Bottom line:** The local repository is a faithful Octave/Conda port of the original MATLAB implementation. The core three-step Shambhala2 algorithm (quantile normalization with P, CuBlock, Q-rescaling) is preserved. The only non-trivial algorithmic difference is the k-means initialization strategy (random vs. k-means++), which is mitigated by CuBlock's 30-iteration averaging. All other changes are either cosmetic or exact mathematical equivalents implemented without toolbox dependencies.
