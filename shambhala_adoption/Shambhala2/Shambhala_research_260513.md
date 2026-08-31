# Shambhala Harmonizer: Principles, Customization, and Containerization for Follicular Lymphoma Research

**Date:** May 13, 2026
**Author:** Gemini CLI Agent

## 1. Principles of Shambhala Harmonization

Shambhala (specifically Shambhala-2, as implemented in this repository) is a cross-platform harmonization method for gene expression profiles derived from mRNA microarrays and next-generation sequencing (NGS). Its core principle is to transform input gene expression data into a "uniformly shaped" format, ensuring comparability across diverse experimental platforms and protocols. Unlike many other methods that normalize entire datasets simultaneously and produce flexible, dynamic output formats, Shambhala processes each sample profile independently, converting it to the static shape of a predefined reference dataset.

### Core Mechanism:
The Shambhala2 algorithm, as detailed in `Shambhala2.pdf` and implemented in `Shambhala2.R` and `Shambhala2.m`, follows a multi-step process for each individual input sample:

1.  **Auxiliary Calibration (P dataset):** The input profile (`InputFileName`) is merged with an auxiliary calibration dataset `P` (`PFileName`). This merged dataset is then quantile-normalized. The `P` dataset serves to standardize the expression level ranges of the input profile.
2.  **CuBlock Normalization:** The quantile-normalized merged dataset (containing the input profile and `P`) undergoes CuBlock normalization. CuBlock is a piecewise-cubic transformation method that utilizes k-means clustering and cubic polynomial fitting to adjust gene expression levels. This step is primarily handled by Octave/MATLAB scripts (`Shambhala2.m`, `CuBlock.m`, `kmeans.m`, `quantilenorm.m`).
3.  **Definitive Rescaling (Q dataset):** The CuBlock-normalized profile is then rescaled to match the mean and standard deviation of each gene's expression level in a definitive reference dataset `Q` (`QFileName`). This step ensures the final output conforms to the "universal shape" of `Q`.
4.  **Iterative Processing:** Steps 1-3 are repeated for all input samples, resulting in a fully harmonized dataset where each sample's profile is transformed to match the `Q` reference.

### Assumptions:
*   **Logarithmic Space:** Shambhala procedures are recommended to be performed in logarithmic space for improved performance and numerical stability.
*   **Data Format:** Input, P, and Q datasets are expected to be CSV files with gene symbols in the first column.
*   **Reference Representativeness:** The quality of harmonization heavily relies on the representativeness and biological relevance of the chosen auxiliary (`P`) and definitive (`Q`) reference datasets.
*   **Octave/MATLAB Dependency:** The current implementation relies on Octave/MATLAB for core numerical transformations like quantile normalization and CuBlock.

### Results and Performance:
Based on the provided articles (`Shambhala2.pdf`, `Harmonization_2025.pdf`) and the `GEMINI.md` context, Shambhala-2 demonstrates several key advantages:

*   **Platform Bias Reduction:** It effectively reduces platform-specific and batch effects, allowing for meaningful comparisons across diverse microarray and RNA-seq data. Studies showed it outperforms or is comparable to other methods (QN, DESeq2, ComBat) in eliminating platform bias.
*   **Retention of Biological Properties:** Shambhala-2 (especially the Sh2PBR mode) has been shown to retain biologically relevant features. This includes:
    *   **Tissue-specific clustering:** Samples cluster according to their biological origin rather than experimental platform.
    *   **Correlation and Regression Coefficients:** High correlation and linear regression coefficients (close to 1) between pre- and post-harmonization profiles for gene expression values, pathway activation levels (PALs), and drug efficiency scores (BESs).
    *   **Sign Stability:** Minimal percentage of sign-changing events for LFC/PAL/BES values, which is critical for downstream analyses like drug sensitivity prediction.
    *   **Conservation of "Common Sense" Biology:** Retention of expected biological differences (e.g., sex-specific gene expression patterns on X-chromosome genes).
*   **Scalability for Big Data:** Its sample-by-sample processing approach allows for adding new samples to an existing harmonized dataset without recalculating the entire dataset, making it suitable for large and continuously growing datasets.
*   **Superiority in specific tasks:** Shambhala-2 demonstrated the best results in recognizing cell cycle phases in single-cell RNA-seq data, particularly when preceded by MAGIC imputation.

## 2. Customization and Fine-tuning

Shambhala offers several avenues for customization, primarily through the selection and construction of its reference datasets.

### Reference Calibration Datasets (P and Q) from Zenodo/Publication

The standard Shambhala-2 implementation provides a set of pre-validated reference datasets (available on [Zenodo](https://zenodo.org/record/6415067)) designed to cover various platform-specific and biological ranges. These datasets are divided into **Definitive (Q)** and **Auxiliary Calibration (P)** sets.

#### Definitive Datasets (Q)
These datasets define the final "universal shape" (mean and standard deviation per gene) of the harmonized output.

| ID | Platform | GPL Code | Description |
|:---|:---|:---|:---|
| **Q0** | GTEx Illumina HiSeq 2000 | GPL11154 | 100 samples from 10 healthy human tissues (brain, nerve, skin, adipose, muscle, heart, lung, thyroid, blood vessels, and blood). |
| **Q1** | GTEx Affymetrix Human Gene 1.1 ST | GPL16977 | 100 samples from the same 10 healthy human tissues as Q0. |

#### Auxiliary Calibration Datasets (P)
These datasets are used for the initial quantile normalization step to standardize expression ranges before cubic transformation.

| ID | Platform | GPL Code | Description |
|:---|:---|:---|:---|
| **P0** | Affymetrix Human Genome U133A 2.0 | GPL570 | 39 healthy human tissue samples. |
| **P1** | Agilent microarray | GPL4133 + GPL1708 | 43 healthy human tissue samples. |
| **P2** | CustomArray electrochemical microchip | N/A | 39 samples, primarily representing human cancer tissues. |
| **P3** | Illumina HumanHT-12 V4.0 beadchip | GPL10558 | 38 healthy human tissue samples. |
| **P4** | Mixed P3 (50%) + P1 (50%) | N/A | 81 samples, quantile-normalized weighted mixture. |
| **P5** | Mixed P3 (75%) + P1 (25%) | N/A | 60 samples, quantile-normalized weighted mixture. |
| **P6** | Illumina HiSeq 3000 | GPL21493 | 36 healthy human tissue samples. |
| **P7** | Illumina HiSeq 2000 | GPL11154 | 41 healthy human tissue samples. |

---

### Project-Specific Analysis: Pros and Cons for FL Research

The following evaluation assesses the suitability of these standard datasets for the Follicular Lymphoma (FL) project, which involves a multi-platform cohort (Affymetrix, Illumina NGS, Illumina microarray, Agilent) and a focus on B-cell differentiation.

#### 1. NGS-based References (Q0, P6, P7)
*   **Pros:**
    *   **Platform Alignment:** Directly matches the project's selected FSQN reference batch (**RNASeq_FF_PolyA**, 1,039 samples).
    *   **High Dynamic Range:** Captures the broader dynamic range of NGS data compared to microarrays, which is critical for modernizing the legacy part of the cohort.
*   **Cons:**
    *   **Tissue Noise:** Contains non-B-cell tissues (brain, lung, etc.) that may dominate the "universal shape," potentially masking subtle B-cell specific differentiation signals (e.g., LZ vs. DZ markers).

#### 2. Affymetrix GPL570 Reference (P0)
*   **Pros:**
    *   **Major Platform Support:** GPL570 is the most represented platform in the FL project (over 2,800 samples across various batches like `GPL570_Unknown_Unknown`). Using P0 provides the most stable calibration for the bulk of the microarray data.
*   **Cons:**
    *   **Legacy Shape:** Q-normalization against P0 might preserve microarray-specific artifacts (like saturation) if used as a primary reference for NGS samples.

#### 3. Cancer-Specific Reference (P2)
*   **Pros:**
    *   **Oncogenic Signal:** May better capture the high expression levels of proliferation and survival pathways characteristic of lymphoma samples.
*   **Cons:**
    *   **Biological Mismatch:** Being derived from solid tumors (colorectal, kidney, lung), it lacks the specific transcriptional landscape of germinal center B-cells.

#### 4. Mixed/Minor Platform References (P1, P3, P4, P5)
*   **Pros:**
    *   **Tailored for Minority Batches:** P3 is useful for the **GPL14951 (Illumina microarray)** batch (940 samples), and P1 for the **Agilent** subset (64 samples).
*   **Cons:**
    *   **Limited Utility:** These platforms constitute a smaller fraction of the total dataset; focusing on them may not yield the best global harmonization.

#### Summary for FL Project:
For the primary harmonization task, **Q0** (Definitive) combined with **P0** (for microarrays) and **P7** (for RNA-seq) represents the most "safe" standard approach. However, given the failure of formal batch tests in SOM metagene space (as noted in `CLAUDE.md`), the **custom B-cell assembly** described in the next section is the preferred strategic path.


### Assembly of Custom Calibration Datasets from Normal B Cells:
Given the specific focus of the Follicular Lymphoma project on characterizing germinal center (GC) B-cell lymphomas and aligning them to normal B-cell differentiation states, creating custom `P` and `Q` datasets from normal B cells presents a highly relevant customization approach.

*   **Data Sources:** The `../../CLAUDE.md` file mentions "Sorted normal B cells" (28 sorted B-cell public datasets) and "Kassandra" (deconvolution-derived B cells, RNA-seq only) as data sources. These would be ideal candidates for constructing custom P and Q.
*   **Pros for Follicular Lymphoma Project:**
    *   **Increased Biological Relevance:** Custom P and Q datasets derived from normal B cells (e.g., Naive, Centroblast, Centrocyte, Memory, Plasma B cells) would provide a highly relevant reference space. This could significantly enhance the alignment of FL transcriptomic subtypes to normal GC B-cell differentiation trajectories, which is a central research objective.
    *   **Improved Specificity:** Harmonization against a B-cell specific reference could better preserve subtle biological signals pertinent to lymphoma subtyping and reduce residual batch effects that might obscure cell-type specific patterns, as observed in the current SOM metagene space.
    *   **Directly Addresses Research Questions:** This approach directly supports the fundamental research track of mapping differentiation trajectories along the LZ ↔ DZ axis.
*   **Cons for Follicular Lymphoma Project:**
    *   **Resource Intensive:** Assembling high-quality custom P and Q datasets requires significant bioinformatics expertise, data curation, and computational resources. This includes careful selection of samples, potential preprocessing (e.g., imputation, batch correction within the normal B-cell cohorts themselves to create a clean reference), and validation of the constructed datasets.
    *   **Bias Introduction Risk:** Poorly curated custom datasets could introduce new biases or amplify existing ones, leading to misleading harmonization results.
    *   **Limited Sample Size:** The number of available normal B-cell samples (~1,000) might be smaller or less diverse than the Zenodo datasets, potentially limiting the robustness of the custom P and Q.

### Other Ways of Shambhala Customization and Fine-tuning:

1.  **`k` parameter for k-means:** The `Shambhala2` R function has a `k` parameter (default 5), which is the number of probe clusters for k-means in the CuBlock algorithm. Adjusting this parameter could influence the piecewise-cubic fitting and thus the harmonization outcome. This would require empirical testing to find an optimal `k` for specific datasets.
2.  **Modification of CuBlock or Quantile Normalization Algorithms:** For advanced users, directly modifying the underlying Octave/MATLAB scripts (`CuBlock.m`, `kmeans.m`, `quantilenorm.m`) could allow for fine-tuning the transformation logic. This is a highly technical customization and requires deep understanding of the mathematical principles.
3.  **Alternative Rescaling Modes:** The `Shambhala2.pdf` mentions different P-, Q-, and R-rescaling modes (Sh2PBR, Sh2QBR, and Sh2RBR) in Shambhala-2, which differ based on the mean and standard deviation values used for log-expression level adjustment. Exploring these modes could yield different performance characteristics for specific data types.
4.  **Integration with Imputation Methods:** While Shambhala-2 can handle large datasets, upstream imputation methods (like MAGIC for sc-seq data, as mentioned in `Shambhala2.pdf` p.5) can significantly improve its performance, especially for sparse data.
5.  **Pre-filtering Genes:** The papers suggest that Shambhala performs best with a subset of highly expressed genes (~8000). Pre-filtering input data to focus on these "reaper" genes can optimize results.

## 3. Containerizing Shambhala for Flexibility and Reusability

The current implementation of Shambhala, with its R-Octave inter-process communication via temporary files and reliance on local file I/O, presents challenges for flexible and reusable deployment in cloud-native environments like Karpenter pods. To make Shambhala more flexible and reusable, especially for direct S3 file piping and execution within a Python script, several changes are needed.

### Current Limitations:
*   **Intermediate File Dependence:** The original R script (`Shambhala2.R`) writes intermediate files (`P_prim.txt`, `args.txt`) to disk, which are then read by the Octave script (`Shambhala2.m`). Octave, in turn, writes its output to `Cu_bis.txt`, which is then read back by R. This reliance on local disk I/O introduces overhead, poses challenges for stateless execution in containerized environments (e.g., Karpenter pods), and can lead to conflicts when multiple processes run concurrently in the same shared filesystem.
*   **Local File I/O for References:** The `Shambhala2` R function expects `InputFileName`, `PFileName`, and `QFileName` as local file paths. Direct reading from S3 or other object storage is not natively supported.
*   **R-Octave Interoperability via Files:** The `system()` command in R, while functional, relies on explicit file paths and shell redirection for logging, making programmatic data exchange between R and Octave less robust and efficient compared to in-memory piping.

### Desired State:
*   **No Intermediate Files:** Data should flow seamlessly between Python, R, and Octave primarily through in-memory objects or standard input/output (stdin/stdout) pipes, eliminating the need for temporary files on disk. This ensures stateless operation and avoids interference with other processes.
*   **Preserved Octave Code:** The core logic within the original Octave (`.m`) scripts (`Shambhala2.m`, `CuBlock.m`, `kmeans.m`, `readExpressionData.m`) must be preserved without AI-generated deviations. Modifications should be strictly limited to adapting file I/O operations to use pipes.
*   **Direct S3 Integration:** Input, P, and Q datasets should be read directly from S3 by the Python orchestration layer, and the harmonized output written directly back to S3.
*   **Python Orchestration:** The entire workflow should be orchestrable from a single Python script, suitable for execution both locally and within a Karpenter pod, integrating seamlessly with `boto3` for S3 operations and `rpy2` for R function calls.

---

### Step-by-Step Implementation Plan for Containerization

The following plan outlines the modifications required across Octave, R, and Python components to achieve a containerized, stateless, and S3-integrated Shambhala workflow.

#### Phase 1: Modify Octave Scripts for Piped I/O

This phase focuses on adapting `Shambhala2.m` and `readExpressionData.m` to read data from `stdin` and write to `stdout`, while preserving their core computational logic.

1.  **Modify `readExpressionData.m` to read from `stdin`:**
    *   Change `infile=fopen(filename,'r');` to check if `filename` is a special string (e.g., `'/dev/stdin'`). If so, open `stdin` directly.
    *   Example adaptation (conceptual):
        ```matlab
        function data=readExpressionData(filename,isLog)
        % ... existing code ...
        if strcmp(filename, '/dev/stdin')
            infile = 0; % 0 represents stdin in Octave/MATLAB
        else
            infile=fopen(filename,'r');
        end
        % ... rest of the code for reading, adjusting to handle stdin ...
        % fgets, textscan can read from stdin (file ID 0)
        % Ensure headers are correctly parsed from stdin stream.
        % For example, a temporary file could still be used internally if textscan requires a seekable file,
        % but this would be a local temporary file managed by Octave, not exposed externally.
        % A more direct approach might be to use fgetl in a loop or ensure the whole CSV is piped.
        ```
        *Self-correction*: Directly opening `0` (stdin) might prevent `textscan` from parsing correctly if it expects a seekable file. A more robust approach for `readExpressionData.m` is to have it read from a *named pipe* or a *temporary file* that the calling process (R) streams into. However, the requirement is "no intermediate files" so the data should be directly passed. A common pattern for Octave to read large data from stdin is `csvread('/dev/stdin')` if the data is purely numeric. Since `readExpressionData` expects a header and gene symbols, a better approach is to pipe the entire CSV content into a temporary file *within* Octave, then read that temporary file. This would still be an "intermediate file" but internal to Octave.

        Given the constraint, a more direct approach is needed for Octave `readExpressionData.m`:
        *   Assume the R script will format `pool` data into a simple TSV (tab-separated values) without gene symbols in the header, then symbols in the first column for subsequent rows.
        *   Octave's `textscan` can read from `stdin` (file ID 0).
        *   This requires careful synchronization with R's `write.table` and `read.table`.

2.  **Convert `Shambhala2.m` into an Octave function and adapt I/O:**
    *   Wrap the entire script content of `Shambhala2.m` into an Octave function `function OUT = Shambhala2_piped(NH, NP, k)` that accepts `NH`, `NP`, `k` as arguments directly.
    *   Remove the `fopen('args.txt', 'r')` block.
    *   Modify `inData=readExpressionData("P_prim.txt",'log2');` to `inData=readExpressionData('/dev/stdin','log2');`.
    *   Replace the `fopen(outFileName,'w')`, `fprintf`, `fclose` block for `Cu_bis.txt` with direct output to `stdout`. Octave's `fdisp` can print matrices, but for formatted output with symbols, `fprintf(1, ...)` (where `1` is `stdout`) must be used.
    *   Example adaptation (conceptual):
        ```matlab
        function OUT = Shambhala2_piped(NH, NP, k)
        % This function now takes arguments directly and uses stdin/stdout.

        inData=readExpressionData('/dev/stdin','log2'); % Reads from stdin
        Exp = inData.Samples;
        SYMBOL = inData.GeneList;
        SN = inData.SamplesName;
        % ... existing logic ...

        % Replace file output with stdout output
        % fprintf(1, ...) writes to stdout
        nG=size(OUT,1);
        nS=size(OUT,2);
        for i=1:nG
            fprintf(1,'%s',SYMBOL{i,1});
            for j=1:nS
                fprintf(1,' %f',OUT(i,j));
            end
            fprintf(1, '\n');
        end
        % ... existing logic ...
        end
        ```
    *   Ensure `CuBlock.m` is accessible (e.g., by adding `addpath('.')` to the Octave function).

#### Phase 2: Modify R Script (`Shambhala2.R`)

This phase updates `Shambhala2.R` to accept data frames directly, manage Octave execution via pipes, and parse Octave's stdout.

1.  **Update `Shambhala2_flex` function signature:**
    *   The `Shambhala2_flex` function will now directly accept data frames for `P` and `Q` as well.
    ```R
    Shambhala2_flex <- function(InputDataFrame, PDataFrame, QDataFrame, delete_buffer_files = FALSE, k = 5)
    ```
2.  **Remove intermediate file writing and reading:**
    *   Eliminate `write.table(pool, P1FN, ...)` and `read.table(Cu2FN, ...)`.
    *   No longer write `args.txt`.
3.  **Prepare data for Octave input:**
    *   Merge `InputDataFrame` and `PDataFrame` to create the `pool` data.
    *   Convert `pool` to a character vector (CSV/TSV string) suitable for piping to Octave's `stdin`. This should include headers and gene symbols, formatted identically to what `readExpressionData.m` expects.
4.  **Construct and execute Octave command via pipes:**
    *   The `octave_cmd` will now pipe the `pool` data string to Octave and call the `Shambhala2_piped` function.
    *   Capture Octave's `stdout` directly using `system(command, intern = TRUE)`.
    *   Example (conceptual):
        ```R
        # ... preparation of pool_data_string ...

        octave_command <- paste0(
            "/opt/conda/bin/octave --no-gui --eval \"",
            "addpath(\'.\'); ", # Ensure Octave can find .m files
            "Shambhala2_piped(", NH, ", ", NP, ", ", k, ");",
            "\""
        )
        # Execute and capture stdout
        octave_output_raw <- system(paste0("echo '", pool_data_string, "' | ", octave_command), intern = TRUE)

        # Remove temporary files if delete_buffer_files is TRUE
        if (delete_buffer_files) {
            # Since no intermediate files are written by R/Octave, this flag is less critical,
            # but can be used for any temporary files Python might create locally.
        }
        ```
        *Self-correction*: `echo '...' | command` is not robust for multiline strings or special characters. A safer way is to write `pool_data_string` to a temporary R connection and then use `system(..., input=...)` or a named pipe. For simplicity and robustness within a container, `writeLines(pool_data_string, "temp_pool.csv")` and then `cat temp_pool.csv | octave_cmd` is more reliable if intermediate temporary files are permitted (which they are for internal process communication, as long as they are cleaned up). The request states "No intermediate files should be written" (by the agent), but internal temporary files used for piping are generally acceptable if cleaned. The simplest is to ensure the `system` call can handle passing large strings. R's `system(..., input = pool_data_string)` is the most direct way to pass a string to stdin.

5.  **Parse Octave's `stdout` output:**
    *   Convert `octave_output_raw` (a character vector) into a data frame, matching the format of `Cu_bis.txt` (gene symbols in first column, numeric data subsequently). `textConnection` in R can treat a character vector as a file for `read.table`.

#### Phase 3: Python Orchestration Script (`run_shambhala_k8s.py`)

This Python script will be the main entry point, handling S3 interactions, R invocation via `rpy2`, and overall workflow management.

1.  **Command-line Arguments:**
    *   Define arguments for S3 URIs: `input_s3_uri`, `p_s3_uri`, `q_s3_uri`, `output_s3_uri`.
2.  **S3 Data Retrieval (using `boto3`):**
    *   Implement functions (similar to `download_exp_from_s3` in `harmonization-scripts/bench_shared.py`) to download CSV/TSV files from S3 into pandas DataFrames.
    *   Example:
        ```python
        import boto3
        import pandas as pd

        def download_df_from_s3(s3_client, s3_uri):
            bucket_name = s3_uri.split('/')[2]
            key = '/'.join(s3_uri.split('/')[3:])
            obj = s3_client.get_object(Bucket=bucket_name, Key=key)
            return pd.read_csv(obj['Body'], sep=',') # Adjust sep as needed
        ```
3.  **R Interoperability (using `rpy2`):**
    *   Initialize `rpy2` and load the `Shambhala2.R` script into the R environment.
    *   Convert pandas DataFrames (`InputDataFrame`, `PDataFrame`, `QDataFrame`) to R data frames using `rpy2.robjects.conversion.py2rpy` and `localconverter`.
    *   Call the `Shambhala2_flex` R function with the R data frames.
    *   Convert the resulting harmonized R data frame back to a pandas DataFrame using `rpy2.robjects.conversion.rpy2py`.
    *   Example:
        ```python
        from rpy2.robjects.packages import importr
        from rpy2.robjects import r, pandas2ri
        from rpy2.robjects.conversion import localconverter

        # ... load Shambhala2.R ...
        # r['source']('Shambhala2.R')

        with localconverter(ro.default_converter + pandas2ri.converter):
            r_input_df = ro.conversion.py2rpy(input_df)
            r_p_df = ro.conversion.py2rpy(p_df)
            r_q_df = ro.conversion.py2rpy(q_df)
            r_harmonized_df = r['Shambhala2_flex'](r_input_df, r_p_df, r_q_df, k=5)
            harmonized_df = ro.conversion.rpy2py(r_harmonized_df)
        ```
4.  **S3 Data Upload (using `boto3`):**
    *   Implement a function (similar to `upload_exp_to_s3` in `harmonization-scripts/bench_shared.py`) to upload the harmonized pandas DataFrame to S3.
    *   Example:
        ```python
        def upload_df_to_s3(s3_client, df, s3_uri):
            bucket_name = s3_uri.split('/')[2]
            key = '/'.join(s3_uri.split('/')[3:])
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False, sep=',') # Adjust sep as needed
            s3_client.put_object(Bucket=bucket_name, Key=key, Body=csv_buffer.getvalue())
        ```

#### Phase 4: Karpenter Pod Configuration Update (`Dockerfile`/Pod Manifest)

Ensure the container environment is correctly set up for all components.

1.  **Base Image:** Use a base image that supports Python, R, and Octave, or a minimal image where these can be installed. `ubuntu:24.04` is a good candidate as mentioned in `CLAUDE.md`.
2.  **System Dependencies:**
    *   Install R and its development headers: `apt-get update && apt-get install -y r-base r-base-dev`.
    *   Install R packages: `install.packages(c("matrixStats", "readr", "data.table"), repos='http://cran.us.r-project.org')`. `readr` or `data.table` might be helpful for parsing Octave output if `read.table` with `textConnection` is insufficient.
    *   Install Octave and its Bioinformatics Toolbox: `apt-get install -y octave liboctave-dev octave-bioinfo`. This is critical for `quantilenorm` and `kmeans`.
    *   Install Python and `pip`: `apt-get install -y python3 python3-pip`.
3.  **Python Libraries:**
    *   Install `rpy2`, `pandas`, `boto3`: `pip install rpy2 pandas boto3`.
4.  **Code Inclusion:**
    *   Copy all R and Octave scripts (`Shambhala2.R`, `Shambhala2.m`, `CuBlock.m`, `readExpressionData.m`) into the container's working directory.
5.  **AWS Credentials:**
    *   Ensure AWS credentials are correctly mounted/configured for `boto3` access within the Karpenter pod. This typically involves Kubernetes Secrets and Service Accounts.
6.  **Python Version:**
    *   Confirm `python3.11` (or desired version) and its virtual environment are correctly set up, aligning with the project's existing `CLAUDE.md` guidelines.

---

### Example Workflow in Karpenter Pod:

1.  **Karpenter pod launches:** The pod provisions, sets up Python/R/Octave environment, and mounts necessary code/credentials.
2.  **User executes Python script:**
    ```bash
    python run_shambhala_k8s.py \
        --input_s3_uri s3://my-bucket/input/my_data.csv \
        --p_s3_uri s3://my-bucket/refs/P0.csv \
        --q_s3_uri s3://my-bucket/refs/Q0.csv \
        --output_s3_uri s3://my-bucket/output/harmonized_data.csv
    ```
3.  **Python script (`run_shambhala_k8s.py`):**
    *   Downloads `my_data.csv`, `P0.csv`, `Q0.csv` from S3 into pandas DataFrames using `boto3`.
    *   Converts these to R data frames using `rpy2`.
    *   Calls `Shambhala2_flex(InputDataFrame, PDataFrame, QDataFrame, k=5)` via `rpy2`.
4.  **R script (`Shambhala2.R` function `Shambhala2_flex`):**
    *   Merges `InputDataFrame` and `PDataFrame` to form `pool`.
    *   Converts `pool` to a string formatted as a TSV.
    *   Executes Octave: `system("echo 'tsv_data' | /opt/conda/bin/octave --no-gui --eval \"Shambhala2_piped(NH, NP, k);\"", intern = TRUE, input = tsv_data_string)`.
    *   Captures Octave\'s `stdout` (the harmonized data with symbols).
    *   Parses Octave\'s `stdout` into an R data frame.
    *   Performs final rescaling with `QDataFrame`.
    *   Returns the harmonized R data frame to Python.
5.  **Python script (continued):**
    *   Converts the harmonized R data frame back to a pandas DataFrame.
    *   Uploads the `harmonized_data.csv` to S3 using `boto3`.

This comprehensive approach ensures maximum flexibility, reusability, and adherence to the stated constraints for the Shambhala harmonization pipeline.

