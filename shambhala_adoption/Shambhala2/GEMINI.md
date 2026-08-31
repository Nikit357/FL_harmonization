# Shambhala2 Project Context

Shambhala2 is a cross-platform harmonizer for gene expression profiles obtained from mRNA microarrays and next-generation sequencing (NGS). It converts profiles to a predefined shape based on a definitive dataset `Q`, using an auxiliary calibration dataset `P`.

## Project Architecture

The project employs a hybrid approach, using R for data orchestration and Octave/MATLAB for core computational tasks.

1.  **Data Preparation (R):** `Shambhala2.R` reads input data, merges it with reference dataset `P`, and writes temporary files (`P_prim.txt`, `args.txt`).
2.  **Core Harmonization (Octave):** `Shambhala2.m` is called by R. It performs:
    *   Quantile normalization using the `Bioinformatics Toolbox`.
    *   CuBlock normalization (via `CuBlock.m`), which uses k-means clustering and cubic polynomial fitting.
    *   Writes results to `Cu_bis.txt`.
3.  **Final Processing (R):** `Shambhala2.R` reads Octave's output, merges it with reference dataset `Q`, and rescales the data (setting mean and standard deviation per gene to match `Q`).

## Technologies & Dependencies

- **R**: Main interface and data processing.
    - Requirement: `matrixStats` package.
- **Octave/MATLAB**: Core numerical computations.
    - Requirement: `Bioinformatics Toolbox` (specifically `quantilenorm`).
    - Note: GNU Octave can be used as a free alternative to MATLAB.
- **Data Format**: CSV files with gene symbols in the first column.

## Key Files

- `Shambhala2.R`: Primary entry point. Contains the `Shambhala2()` function.
- `Shambhala2.m`: Main Octave script for CuBlock and quantile normalization.
- `CuBlock.m`: Implementation of the CuBlock normalization method.
- `readExpressionData.m`: Octave helper to read gene expression matrices.
- `P0.csv`, `Q0.csv`: Reference datasets used for calibration and definitive shaping.
- `Input.csv`: Example input data.

## Usage

### R Function Signature

```r
Shambhala2 <- function(InputFileName, PFileName, QFileName, delete_buffer_files = TRUE, k = 5)
```

- `InputFileName`: Path to the CSV file containing samples to harmonize.
- `PFileName`: Path to the calibration dataset (e.g., `P0.csv`).
- `QFileName`: Path to the definitive dataset (e.g., `Q0.csv`).
- `delete_buffer_files`: If TRUE (default), removes temporary files (`P_prim.txt`, `args.txt`, `Cu_bis.txt`) after execution.
- `k`: Number of probe clusters for k-means (default 5).

### Execution

The function is typically executed within an R environment:

```r
source("Shambhala2.R")
Harmonized <- Shambhala2("Input.csv", "P0.csv", "Q0.csv")
write.table(Harmonized, "Output.csv", col.names = TRUE, row.names = FALSE, sep =",")
```

## Development Conventions

- **Inter-process Communication**: R and Octave communicate via temporary text files.
- **Error Logging**: Octave output is redirected to `octave_debug.log`.
- **Scaling**: For large datasets, processing is performed sample-by-sample, which can be time-consuming. Parallelization may be considered for future improvements.
- **File Handling**: Ensure the Octave executable path in `Shambhala2.R` matches your environment (currently set to `/opt/conda/bin/octave`).
