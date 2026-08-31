import glob
import io
import itertools
import math
import os
import pickle
import subprocess
import warnings
from pathlib import Path
from statistics import median

import boto3
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import display
from scipy.stats import norm
from supervenn import supervenn
from tqdm import tqdm
from tqdm.notebook import tqdm as tqdm_notebook

plt.rcParams["pdf.fonttype"] = "truetype"
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["figure.dpi"] = 200

sns.set_style("ticks")
sns.axes_style("white")

# Cohort assembly originally ran against an internal cohort database, configured here
# with an API key. The public pipeline reads the prepared expression/annotation pair
# directly from TSV (see FL_DATA_ROOT below), so no client and no credential is needed.

import pyreadr
import rpy2.robjects as ro
from biomart import BiomartServer
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr
from scipy.interpolate import interp1d
from sklearn.cluster import AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Directory holding the prepared expression/annotation TSVs. It lived on internal
# shared storage; set FL_DATA_ROOT to wherever the pair is staged.
FL_DATA_ROOT = os.environ.get("FL_DATA_ROOT", ".")

comb_exp = pd.read_csv(
    os.path.join(FL_DATA_ROOT, "comb_exp.tsv"), sep="\t"
).set_index("Unnamed: 0")
comb_ann = pd.read_csv(
    os.path.join(FL_DATA_ROOT, "comb_ann.tsv"), sep="\t"
).set_index("Unnamed: 0")


bad_batches = ["GPL14951_FFPE_Unknown", "GPL8432_FFPE_Unknown", "GPL13938_FFPE_Unknown"]
bad_cohorts = ["SOM"]


# "GPL8432_FFPE_Unknown",
# "GPL6244_FFPE_Unknown",
# "GPL17586_FF_Unknown",
# "GPL20188_FF_Unknown",
# "GPL23541_FF_Unknown",
# "GPL887_FFPE_Unknown",
# "GPL26356_FF_Unknown",
# "GPL17047_FF_Unknown",
# "GPL6244_FF_Unknown",
# "GPL13938_FFPE_Unknown",
# ]
rare_groups = [
    "Extranodal_Marginal_Zone_Lymphoma",
    "Double_Hit_Lymphoma",
    "Mantle_Cell_Lymphoma",
    "Chronic_Lymphocytic_Leukemia",
    "Other",
]


comb_ann = comb_ann[~comb_ann.RNA_BATCH.isin(bad_batches)]
comb_ann = comb_ann[~comb_ann.Major_group.isin(rare_groups)]
comb_ann = comb_ann[~comb_ann.COHORT_LABEL.isin(bad_cohorts)]

comb_ann.loc[
    comb_ann.Major_group.isin(["Normal_B_cells", "Kassandra"]),
    ["Major_group"],
] = "Normal_B_cells"


common_samples = comb_exp.index.intersection(comb_ann.index)  # [:7000]
filtered_exp = comb_exp.loc[common_samples].dropna(axis=1)
filtered_exp = filtered_exp.loc[~filtered_exp.index.duplicated(keep="first"), :]
# Handle NaNs if necessary
batch_groups = comb_ann.loc[common_samples, "RNA_BATCH"]
batch_groups = batch_groups.loc[~batch_groups.index.duplicated(keep="first"),]
comb_ann_dedup = comb_ann.loc[~comb_ann.index.duplicated(keep="first"), :]

def fsqn_normalize(data, groups, target_group=None):
    """
    Implementation of Feature Specific Quantile Normalization (FSQN).
    FSQN transforms the distribution of each feature (gene) within each group
    to match a target distribution (either a specific group or the global mean).

    Parameters:
    -----------
    data : pd.DataFrame
        Gene expression data (Samples as rows, Genes as columns).
    groups : pd.Series or list
        The grouping variable (e.g., RNA_BATCH).
    target_group : str, optional
        The name of the group to use as the reference distribution.
        If None, the global average distribution across all samples is used.

    Returns:
    --------
    pd.DataFrame
        FSQN-normalized expression data.
    """
    # Align groups with data index
    if not isinstance(groups, pd.Series):
        groups = pd.Series(groups, index=data.index)
    groups = groups.loc[data.index]

    unique_groups = np.unique(groups)
    normalized_data = data.copy()

    # 1. Define the target distribution
    # FSQN usually targets the distribution of a 'reference' batch or the global mean
    if target_group and target_group in unique_groups:
        target_dist = np.sort(data.loc[groups == target_group].values, axis=1).mean(
            axis=0
        )
    else:
        # Use global mean distribution as target
        target_dist = np.sort(data.values, axis=1).mean(axis=0)

    n_genes = data.shape[1]
    # Create an interpolation line for the target distribution
    target_ranks = np.linspace(0, 1, n_genes)

    # 2. Normalize each group to the target
    for g in unique_groups:
        group_indices = data.index[groups == g]
        group_data = data.loc[group_indices].values

        for i in range(len(group_indices)):
            sample_values = group_data[i, :]
            # Get the rank order of values in the current sample
            order = np.argsort(sample_values)

            # Map the target distribution values onto the sample's ranks
            # This forces the sample to have the target distribution
            normalized_data.loc[group_indices[i]].iloc[order] = target_dist

    return normalized_data

normalized_fsqn = fsqn_normalize(filtered_exp, comb_ann_dedup["RNA_BATCH"])

# Activate the pandas to R data frame conversion
pandas2ri.activate()

def batch_correct_for_som(data, annotation, batch_col='RNA_BATCH'):
    """
    Performs batch correction highly suitable for the SOM approach using limma::removeBatchEffect.
    SOM is sensitive to absolute expression shifts; limma effectively centers these 
    shifts while maintaining biological structure.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Gene expression data (Samples as rows, Genes as columns).
    annotation : pd.DataFrame
        Sample annotations.
    batch_col : str
        Column containing the batch variables.
        
    Returns:
    --------
    pd.DataFrame
        Batch-corrected expression data.
    """
    print("Loading R package 'limma' for batch correction...")
    limma = importr('limma')
    base = importr('base')
    
    # Transpose data so Genes are rows and Samples are columns (standard R format)
    X = data.T
    common_idx = X.columns.intersection(annotation.index)
    X = X[common_idx]
    
    # Convert to R Matrix
    r_X = pandas2ri.py2rpy(X)
    r_X_mat = base.as_matrix(r_X)
    
    # Extract batches
    batches = annotation.loc[common_idx, batch_col].astype(str).values
    r_batches = ro.StrVector(batches)
    
    # Run limma::removeBatchEffect
    print(f"Applying batch correction for {batch_col}...")
    corrected_r = limma.removeBatchEffect(r_X_mat, batch=r_batches)
    
    # Convert back to pandas DataFrame and transpose back (Samples as rows)
    # rpy2 often auto-converts R matrices to numpy arrays when pandas2ri is active
    if isinstance(corrected_r, np.ndarray):
        corrected_matrix = corrected_r
    else:
        corrected_matrix = pandas2ri.rpy2py(corrected_r)
        
    corrected_df = pd.DataFrame(corrected_matrix, index=X.index, columns=X.columns).T
    
    return corrected_df


def run_opossom_analysis(data, annotation, group_col='Major_group', dataset_name='MyCohort'):
    """
    Runs the full oposSOM pipeline natively in R via rpy2.
    It generates all SOM pictures, HTML reports, and tables in the current working directory.
    
    Parameters:
    -----------
    data : pd.DataFrame
        Gene expression data (Samples as rows, Genes as columns) - optimally batch-corrected.
    annotation : pd.DataFrame
        Sample annotations.
    group_col : str
        Biological grouping column for coloring and spot analysis.
        
    Returns:
    --------
    env : rpy2.robjects.environments.Environment
        The R environment containing the full oposSOM state.
    metagenes_df : pd.DataFrame
        Expression matrix of the SOM metagenes (Metagenes as rows, Samples as cols).
    bmu_df : pd.DataFrame
        Mapping of original Genes to their Best Matching Unit (Metagene).
    """
    print("Loading R package 'oposSOM'...")
    oposSOM = importr('oposSOM')
    base = importr('base')
    
    # Transpose to [Genes x Samples]
    X = data.T
    common_idx = X.columns.intersection(annotation.index)
    X = X[common_idx]
    
    # Convert Data and Groups to R objects
    r_X = pandas2ri.py2rpy(X)
    r_X_mat = base.as_matrix(r_X)
    
    groups = annotation.loc[common_idx, group_col].astype(str).values
    r_groups = ro.StrVector(groups)
    
    # Define oposSOM preferences
    # These trigger the full comprehensive analysis (portraits, spots, reports)
    pref = ro.ListVector({
        'dataset.name': dataset_name,
        'dim.1stLvlSom': 'automatic',
        'standard.spot.modules': 'kmeans',
        'adjust.expression.values': False, # Set to False if already batch-corrected
        'feature.centralization': True,
        'sample.quantile.normalization': True
    })
    
    print("Initializing oposSOM environment...")
    env = oposSOM.opossom_new(pref)
    
    # Inject data into the R environment
    env['indata'] = r_X_mat
    env['group.labels'] = r_groups
    
    # Execute the massive oposSOM run function
    print("Running full oposSOM pipeline. This will generate PDFs and reports locally...")
    oposSOM.opossom_run(env)
    
    # --- Extract Results Back to Python ---
    print("Extracting Metagene matrix and Gene mappings...")
    
    # 1. Metagene matrix
    metagenes_r = env['metadata']
    metagenes_mat = metagenes_r if isinstance(metagenes_r, np.ndarray) else pandas2ri.rpy2py(metagenes_r)
    metagenes_df = pd.DataFrame(metagenes_mat, columns=X.columns)
    metagenes_df.index = [f"Metagene_{i+1}" for i in range(metagenes_df.shape[0])]
    
    # 2. Gene to Metagene mapping (Best Matching Unit)
    som_result = env['som.result']
    bmu_r = som_result.rx2('feature.BMU')
    bmu_arr = bmu_r if isinstance(bmu_r, np.ndarray) else pandas2ri.rpy2py(bmu_r)
    bmu_df = pd.DataFrame({'Best_Matching_Unit': bmu_arr}, index=X.index)
    
    return env, metagenes_df, bmu_df


def cluster_metagenes(metagenes_df, n_clusters=15):
    """
    Performs unsupervised clustering of the extracted metagenes.
    
    Parameters:
    -----------
    metagenes_df : pd.DataFrame
        The metagene expression matrix (Metagenes as rows).
    n_clusters : int
        Number of super-clusters to form.
        
    Returns:
    --------
    pd.DataFrame
        The metagenes assigned to their unsupervised clusters.
    """
    print(f"Clustering {metagenes_df.shape[0]} metagenes into {n_clusters} clusters...")
    
    # Using Agglomerative (Hierarchical) Clustering which is standard for SOM nodes
    clusterer = AgglomerativeClustering(n_clusters=n_clusters, metric='euclidean', linkage='ward')
    labels = clusterer.fit_predict(metagenes_df.values)
    
    cluster_df = pd.DataFrame({
        'Metagene_Cluster': labels
    }, index=metagenes_df.index)
    
    return cluster_df


def retrieve_and_score_genesets(env, keywords=None):
    """
    Retrieves the full list of genesets used by oposSOM, allows filtering by keywords,
    and returns the sample-wise Gene Set Z-scores (GSZ) calculated during the run.
    
    Parameters:
    -----------
    env : rpy2.robjects.environments.Environment
        The oposSOM environment after running opossom_run.
    keywords : list of str, optional
        Only return genesets that contain these keywords (e.g., ['KEGG', 'B_CELL']).
        
    Returns:
    --------
    available_genesets : list
        List of geneset names matching the criteria.
    gsz_scores_df : pd.DataFrame
        The GSZ (Gene Set Z-score) matrix for the selected genesets across all samples.
    """
    print("Retrieving Gene Set Enrichment scores...")
    
    # Extract the full list of geneset names
    gs_list = env['gs.def.list']
    all_genesets = list(gs_list.names)
    
    # Filter by keywords if provided
    if keywords:
        selected_genesets = [
            name for name in all_genesets 
            if any(k.lower() in name.lower() for k in keywords)
        ]
    else:
        selected_genesets = all_genesets
        
    print(f"Found {len(selected_genesets)} genesets matching your criteria.")
    
    # Extract the GSZ scores matrix computed by oposSOM
    gsz_r = env['samples.GSZ.scores']
    gsz_mat = gsz_r if isinstance(gsz_r, np.ndarray) else pandas2ri.rpy2py(gsz_r)
    gsz_df = pd.DataFrame(gsz_mat)
    
    # Assign row names (genesets) and column names (samples)
    gsz_df.index = list(gsz_r.rownames)
    gsz_df.columns = list(gsz_r.colnames)
    
    # Filter the dataframe to only include the selected genesets
    filtered_gsz_df = gsz_df.loc[selected_genesets]
    
    return selected_genesets, filtered_gsz_df

env, metagenes_matrix, gene_to_metagene_map = run_opossom_analysis(
     normalized_fsqn, comb_ann, group_col='Major_group'
 )

#env.to_csv('env.csv')
metagenes_matrix.to_csv('metagenes_matrix.csv')
gene_to_metagene_map.to_csv('gene_to_metagene_map.csv')

# 3. Unsupervised Clustering of Metagenes
metagene_clusters = cluster_metagenes(metagenes_matrix, n_clusters=15)
#
# 4. Geneset Enrichment Scores Retrieval
pathways, pathway_scores = retrieve_and_score_genesets(env, keywords=['HALLMARK', 'KEGG'])

pathways.to_csv('pathways.csv')
pathway_scores.to_csv('pathway_scores.csv')
