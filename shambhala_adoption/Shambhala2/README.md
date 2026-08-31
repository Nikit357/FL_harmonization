# Shambhala2 user’s manual

Shambhala2 is a harmonizer of gene expression profiles obtained via both mRNA microarray hybridization ane next-generation sequencing.
It coverts all the profiles one-by-one, independently one from another, to a predefined shape that is set by the defnitive dataset `Q`.

To provide robust result, such conversion is preformed within the auxiliary calibration dataset `P`.

One-by-one, each profile that needs to be harmonized, is first quantile-normalized (Bolstad et al., 2003, doi:10.1093/bioinformatics/19.2.185) with the dataset `P`. Then the result, `P_prim` is normalized according to CuBlock method (Junet et al, 2021, doi:10.1093/bioinformatics/btab105). Then, from the CuBlock-normalized result (`P_bis`), we take only the profile to be harmonized, and rescale gene expression level. to set the mean and standard deviation of the expression level of each gene `g` equal to mean value and standard deviation of gene `g` expression level in the definitive dataset `Q`.

After it, we repeat the procedure for all other profiles that have to be harmonized.


## Executable scripts

The deposited R functuion

`Shambhala2 = function(InputFileName, PFileName, QFileName, delete_buffer_files = TRUE, k = 5 )` calls MATLAB (R) applications `Shambhala2.m`, `CuBock.m` and `readExpressionData.m`.

`k` is the number of probe clusters for the application of k-means to find probe-cluster partitions. By default it is 5.
  
## Prerequisites 

R: requires `matrixStats` package:

```
install.packages("matrixStats")

```

MATLAB (R) requires method `quantilenorm` (https://www.mathworks.com/help/bioinfo/ref/quantilenorm.html) 
from the `Bioinformatics Toolbox` (https://www.mathworks.com/help/bioinfo/index.html?s_tid=CRUX_lftnav) 

MATLAB (R) licence is free for educational institutions. Those who do not have access to MATLAB (R) licence, may try to use GNU Octave instead.

### Expected computation time

Please note that execution of code may be time-consuming due to harmonization if each profile one-by-one. For example, processing the file `Input.csv` takes about two minutes at an Ubuntu 20.04.2 LTS machine with Intel® Core™ i7-7700K CPU @ 4.20GHz × 8 CPU's and 31,2 GiB or RAM. Therefore, parallel execution of the code may be a good idea. 

## Output data 

The function returns a harmonized gene expression matrix
