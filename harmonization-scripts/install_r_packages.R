options(
    repos = c(CRAN = "https://cloud.r-project.org"),
    Ncpus = parallel::detectCores(),
    warn  = 1
)

if (!requireNamespace("BiocManager", quietly = TRUE))
    install.packages("BiocManager")
BiocManager::install(version = "3.22", ask = FALSE, update = FALSE)

# remotes must be installed before FSQN (GitHub-only since CRAN archive)
if (!requireNamespace("remotes", quietly = TRUE))
    install.packages("remotes")

install.packages(c(
    "missForest",
    "softImpute",
    "DWDLargeR",
    "huge"
), dependencies = TRUE)

# FSQN is no longer on CRAN; install from the author's GitHub repo
remotes::install_github("jenniferfranks/FSQN", upgrade = "never")

BiocManager::install(c(
    "limma",
    "sva",
    "RUVSeq",
    "batchelor",
    "qsmooth",
    "edgeR",
    "DESeq2",
    "ruv",
    "NOISeq",
    "FAbatch",
    "Harman"
), ask = FALSE, update = FALSE)

remotes::install_github("greenelab/TDM",            upgrade = "never")
remotes::install_github("HSU-HPC/HarmonizR",        upgrade = "never")
remotes::install_github("mengqinxue/DBNorm",         upgrade = "never")
remotes::install_github("bioFAM/reComBat",           upgrade = "never")
remotes::install_github("JoevVan/AMDBNorm",          upgrade = "never")
remotes::install_github("zhanglabNKU/DASC",          upgrade = "never")
remotes::install_github("syspremed/exploBATCH",      upgrade = "never")

pkgs    <- c("missForest", "softImpute", "DWDLargeR", "huge", "FSQN",
             "limma", "sva", "RUVSeq", "batchelor",
             "qsmooth", "edgeR", "DESeq2",
             "ruv", "NOISeq", "FAbatch", "Harman",
             "TDM", "HarmonizR", "DBNorm", "reComBat", "AMDBNorm",
             "DASC", "exploBATCH")
missing <- pkgs[!sapply(pkgs, requireNamespace, quietly = TRUE)]
if (length(missing)) {
    stop("Failed to install: ", paste(missing, collapse = ", "))
} else {
    cat("All R packages installed successfully.\n")
}
