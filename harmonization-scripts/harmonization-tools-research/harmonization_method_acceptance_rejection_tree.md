# Harmonization Method Acceptance/Rejection Tree

Compiled from every file in `harmonization-tools-research/` and `implementation-plans-old/`, cross-checked against the 39-method `METHODS` registry in `bench_shared.py`. Links are attached to every named method: a repository (GitHub/CRAN/Bioconductor/PyPI) where one exists, and/or the originating publication (DOI/PubMed). Where the project's own notes gave no external citation, the source review document is linked instead and flagged as "no independent citation found — traced to the review paper only."

**Total tools researched: 75** — **31 adopted**, **44 rejected** (36 at literature/feasibility screening, before any code was written; 8 after an implementation attempt).

---

## 1. Decision tree (numbers)

```
75 tools researched
│
├── 31 ADOPTED — implemented, producing valid results in the benchmark
│
└── 44 REJECTED
    │
    ├── STAGE 1 — Literature/feasibility screening (36)
    │   │
    │   ├── (14) Wrong data modality / architecture
    │   ├── (7)  Requires matched/paired/bridge samples
    │   ├── (5)  Output is not a corrected expression matrix
    │   ├── (5)  Redundant with / inferior to / superseded by an adopted method
    │   ├── (3)  No maintained/accessible software at screening time
    │   └── (3)  Reported to actively harm signal
    │
    └── STAGE 2 — Post-implementation exclusion (8)
        │
        ├── (2) No maintained/accessible software, discovered on the pod
        ├── (2) Architecturally/structurally incompatible, discovered on the pod
        ├── (3) Infra/deployment drift (code fixed, pod manifest never synced)
        └── (1) Unresolved — needs re-verification
```

---

## 2. Adopted (31) — implemented, in the benchmark registry

| Method | Registry key | Link(s) |
|---|---|---|
| No harmonization (passthrough) | `01_raw` | — (trivial baseline, no citation) |
| Median Scaling | `02_median_scaling` | [Kappal 2019, self-published methods note](https://independent.academia.edu/SunilKappal) — not peer-reviewed; verify before citing in a dissertation |
| limma (`removeBatchEffect`) | `03_limma` | [Ritchie et al. 2015, *Nucleic Acids Res* 43(7):e47, DOI](https://doi.org/10.1093/nar/gkv007) · [Bioconductor](https://bioconductor.org/packages/limma) |
| SVA (Surrogate Variable Analysis) | `04_sva` | [Leek & Storey 2007, *PLoS Genet*, PMID 17907809](https://pubmed.ncbi.nlm.nih.gov/17907809/) · [Leek et al. 2012, *Bioinformatics*, PMID 22257669](https://pubmed.ncbi.nlm.nih.gov/22257669/) · [Bioconductor](https://bioconductor.org/packages/sva) |
| ComBat | `05_combat` | [Johnson, Li & Rabinovic 2007, *Biostatistics*, PMID 16632515](https://pubmed.ncbi.nlm.nih.gov/16632515/) · part of [Bioconductor `sva`](https://bioconductor.org/packages/sva) |
| ComBat-seq | `06_combat_seq` | [Zhang, Parmigiani & Johnson 2020, *NAR Genom Bioinform* 2(3):lqaa078, DOI](https://doi.org/10.1093/nargab/lqaa078) · [GitHub](https://github.com/zhangyuqing/ComBat-seq) |
| pyComBat | `07_pycombat` | [Behdenna, Colange, Haziza et al. 2023, *BMC Bioinformatics* 24:459, PMID 38057718](https://pubmed.ncbi.nlm.nih.gov/38057718/) · [GitHub](https://github.com/epigenelabs/pyComBat) — note: `bench_shared.py`'s docstring attributes this to "Müller et al. 2023," which does not match the actual author list; please correct |
| InMoose ComBat-seq | `08_inmoose_combatseq` | [Colange et al. 2025, *Sci Rep*, DOI](https://doi.org/10.1038/s41598-025-03376-y) · [GitHub](https://github.com/epigenelabs/inmoose) |
| RUV (RUVSeq, `RUVg`) | `09_ruv` | [Risso, Ngai, Speed & Dudoit 2014, *Nat Biotechnol* 32:896–902](https://www.nature.com/articles/nbt.2931) · [Bioconductor](https://bioconductor.org/packages/RUVSeq) |
| MNN (`fastMNN`, `batchelor`) | `10_mnn` | [Haghverdi, Lun, Morgan & Marioni 2018, *Nat Biotechnol*, PMID 29608177](https://pubmed.ncbi.nlm.nih.gov/29608177/) · [Bioconductor](https://bioconductor.org/packages/batchelor) |
| Harmony | `11_harmony` | [Korsunsky et al. 2019, *Nat Methods* 16:1289–1296, DOI](https://doi.org/10.1038/s41592-019-0619-0) · [GitHub](https://github.com/immunogenomics/harmony) · [PyPI `harmonypy`](https://pypi.org/project/harmonypy/) |
| Scanorama | `12_scanorama` | [Hie, Bryson & Berger 2019, *Nat Biotechnol*, PMID 31061482](https://pubmed.ncbi.nlm.nih.gov/31061482/) · [GitHub](https://github.com/brianhie/scanorama) · [PyPI](https://pypi.org/project/scanorama/) |
| FSMVN (Feature-Specific Mean-Variance Normalization) | `13_fsmvn` | [Skubleny et al. 2024, *BMC Bioinformatics* 25, DOI](https://doi.org/10.1186/s12859-024-05759-w) |
| qsmooth (smooth quantile normalization) | `14_qsmooth` | [Hicks et al. 2018, *Biostatistics*, PMID 29036413](https://pubmed.ncbi.nlm.nih.gov/29036413/) · [Bioconductor](https://bioconductor.org/packages/qsmooth) |
| FSQN (Python) | `15_fsqn_py` | [Franks, Cai & Whitfield 2018, *Bioinformatics*, PMID 29360996](https://pubmed.ncbi.nlm.nih.gov/29360996/) |
| FSQN (R) | `16_fsqn_r` | same paper as above · [GitHub](https://github.com/jenniferfranks/FSQN) (no tagged release) |
| Quantile Normalization | `17_quantile` | [Bolstad, Irizarry, Åstrand & Speed 2003, *Bioinformatics* 19(2):185–193, DOI](https://doi.org/10.1093/bioinformatics/19.2.185) |
| Rank Normalization | `18_rank` | [Qiu, Wu & Hu 2013, *BMC Bioinformatics* 14:124, PMID 23578321, DOI](https://doi.org/10.1186/1471-2105-14-124) |
| TDM (Training Distribution Matching) | `19_tdm` | [Thompson, Tan & Greene 2016, *PeerJ* 4:e1621, PMID 26844019, DOI](https://doi.org/10.7717/peerj.1621) · [GitHub](https://github.com/greenelab/TDM) |
| Shambhala-2 | `20_shambhala` | [Borisov et al. 2022, *Biomedicines* 10(9):2318, DOI](https://doi.org/10.3390/biomedicines10092318) · [GitHub `BorisovNM/Shambhala2`](https://github.com/BorisovNM/Shambhala2) (no tagged release) |
| HarmonizR | `21_harmonizr` | [Voß, Schlumbohm et al. 2022, *Nat Commun*, PMID 35725563](https://pubmed.ncbi.nlm.nih.gov/35725563/) · [GitHub](https://github.com/HSU-HPC/HarmonizR) |
| TMM (`edgeR`) | `22_tmm` | [Robinson & Oshlack 2010, *Genome Biol* 11:R25, PMID 20196867](https://pubmed.ncbi.nlm.nih.gov/20196867/) · [Bioconductor](https://bioconductor.org/packages/edgeR) |
| VST (`DESeq2`) | `23_vst` | [Love, Huber & Anders 2014, *Genome Biol* 15:550, PMID 25516281](https://pubmed.ncbi.nlm.nih.gov/25516281/) · [Bioconductor](https://bioconductor.org/packages/DESeq2) |
| Angel (rank-percentile + platform-variance filter) | `25_angel` | [Angel et al. 2020, *PLOS Comput Biol* 16(9):e1008219, DOI](https://doi.org/10.1371/journal.pcbi.1008219) · code: [Stemformatics `s4m_pyramid`](https://bitbucket.org/stemformatics/s4m_pyramid/src/master/scripts/atlas.py) |
| XPN (Cross-Platform Normalization) | `26_xpn` | [Shabalin, Tjelmeland, Fan, Perou & Nobel 2008, *Bioinformatics* 24(9):1154–1160, DOI](https://doi.org/10.1093/bioinformatics/btn131) · original source [genome-publications.bioinf.unc.edu/xpn](https://genome-publications.bioinf.unc.edu/xpn/) |
| DWD (Distance-Weighted Discrimination) | `27_dwd` | Original method: [Marron, Todd & Ahn 2007, *JASA*] (no DOI found in project docs) · application to batch adjustment: [Benito et al. 2004, *Bioinformatics*, DOI](https://doi.org/10.1093/bioinformatics/btg385) · large-scale solver used here: [Lam, Marron, Sun & Toh 2018, arXiv:1604.05473](https://arxiv.org/abs/1604.05473) · [CRAN `DWDLargeR`](https://cran.r-project.org/package=DWDLargeR) — note: the in-code docstring cites this as "Qing & Marron 2018," which does not match; please confirm |
| NPN (Nonparanormal Normalization) | `28_npn` | [Liu, Lafferty & Wasserman 2009, *JMLR* 10:2295–2328](https://www.jmlr.org/papers/v10/liu09a.html) · R engine: [Zhao et al. 2012, `huge`, CRAN](https://cran.r-project.org/package=huge) |
| M-ComBat (ComBat with `ref.batch`) | `29_combat_ref` | Base model: [Johnson, Li & Rabinovic 2007, PMID 16632515](https://pubmed.ncbi.nlm.nih.gov/16632515/); the specific "M-ComBat" naming/description used in this project traces to [Yu, Mai, Zheng & Shi 2024, *Genome Biol* 25:254, DOI](https://doi.org/10.1186/s13059-024-03401-9) — **this resolves the earlier open question**: the draft table's "(Zhang X 2024)" citation was a mix-up with `33_amdbnorm`; the correct source for the "M-ComBat" name is the Yu 2024 review itself |
| reComBat | `30_recombat` | [Ognjenovic/BorgwardtLab team, *Bioinformatics Advances* 2(1):vbac071, 2022, DOI](https://doi.org/10.1093/bioinformatics/btac071) · [GitHub `BorgwardtLab/reComBat`](https://github.com/BorgwardtLab/reComBat) (correct repo — not `bioFAM/reComBat`, which is cited in error in both `install_r_packages.R` and the Yu 2024 review notes) |
| RUV-III-PRPS | `31_ruv3prps` | [Molania et al. 2022, *Nat Biotechnol*, PMID 35277707](https://pubmed.ncbi.nlm.nih.gov/35277707/) ("Removing unwanted variation from large-scale RNA sequencing data with PRPS") · [Bioconductor `ruv`](https://bioconductor.org/packages/ruv) |
| AMDBNorm | `33_amdbnorm` | [Zhang, Ye, Chen & Qiao 2022, *Brief Bioinform* 23(1):bbab528, PMID 34958674](https://pubmed.ncbi.nlm.nih.gov/34958674/) · [GitHub `JoevVan/AMDBNorm`](https://github.com/JoevVan/AMDBNorm) + dependency [GitHub `mengqinxue/DBNorm`](https://github.com/mengqinxue/DBNorm) |
| ARSyN | `34_arsyn` | [Nueda, Ferrer & Conesa 2012, *Biostatistics* 13(3):553–566, PMID 22085896](https://pubmed.ncbi.nlm.nih.gov/22085896/) · [Bioconductor `NOISeq`](https://bioconductor.org/packages/NOISeq) |
| FAbatch (`bapred::fabatch()`) | `37_fabatch` | [Hornung, Boulesteix & Causeur 2016, *BMC Bioinformatics* 17:27, PMID 26753519](https://pubmed.ncbi.nlm.nih.gov/26753519/) · [CRAN `bapred`](https://cran.r-project.org/package=bapred) |
| Harman | `38_harman` | [Oytam, Sobhanmanesh, Duesing, Bowden & Osmond-McLeod 2016, *BMC Bioinformatics* 17:332, PMID 27585881, DOI](https://doi.org/10.1186/s12859-016-1212-5) · [Bioconductor `Harman`](https://bioconductor.org/packages/Harman) |
| Procrustes | `39_procrustes` | [Kotlov et al. 2024, *Commun Biol* 7:389, PMID 38555407](https://pubmed.ncbi.nlm.nih.gov/38555407/) · [GitHub `BostonGene/Procrustes`](https://github.com/BostonGene/Procrustes) (no tagged release) |

† `39_procrustes` is included above though outside your original 01–38 numbering; it is the 39th registry entry in `bench_shared.py`.

---

## 3. Rejected — Stage 1: literature/feasibility screening (36, never implemented)

### 3a. Wrong data modality / architecture (14)

| Tool | Link(s) |
|---|---|
| HARP | [Nozari et al. 2025, *Bioinformatics* 41(9):btaf455, DOI](https://doi.org/10.1093/bioinformatics/btaf455) · [GitHub `spang-lab/harp`](https://github.com/spang-lab/harp) · [companion `spang-lab/harplication`](https://github.com/spang-lab/harplication) |
| MoDAmix | [*Sci Rep* 2026, DOI](https://www.nature.com/articles/s41598-026-42355-9) · [GitHub `cbi-bioinfo/MoDAmix`](https://github.com/cbi-bioinfo/MoDAmix) |
| scBatch | [Fei & Chen 2020, *Bioinformatics* 36(10):3115–3123, DOI](https://doi.org/10.1093/bioinformatics/btaa097) · [GitHub `tengfei-emory/scBatch`](https://github.com/tengfei-emory/scBatch) |
| RNABC | [Pedersen, Nielsen, Rossing & Olsen 2018, *Mol Oncol* 12(12):2136–2146, DOI](https://doi.org/10.1002/1878-0261.12389) · [code, Bitbucket `cbligaard/rnabc`](https://bitbucket.org/cbligaard/rnabc/) |
| CSN | [Feldman, Ner-Gaon, Treister & Shay 2024, *PLoS ONE* 19(9):e0307997, DOI](https://doi.org/10.1371/journal.pone.0307997) — paper reports no code release |
| fRMA | [McCall, Bolstad & Irizarry 2010, *Biostatistics* 11(2):242–253, PMID 20097884](https://pubmed.ncbi.nlm.nih.gov/20097884/) · [Bioconductor `frma`](https://bioconductor.org/packages/frma) |
| scGen | [Lotfollahi, Wolf & Theis 2019, *Nat Methods* 16:715–721, PMID 31363220, DOI](https://doi.org/10.1038/s41592-019-0494-8) · [GitHub `theislab/scgen`](https://github.com/theislab/scgen) |
| scVI | [Lopez et al. 2018, *Nat Methods* 15:1053–1058, PMID 30504886, DOI](https://doi.org/10.1038/s41592-018-0229-2) · [GitHub `scverse/scvi-tools`](https://github.com/scverse/scvi-tools) |
| DESC | [Li et al. 2020, *Nat Commun* 11:2338, DOI](https://doi.org/10.1038/s41467-020-15851-3) · [GitHub `eleozzr/desc`](https://github.com/eleozzr/desc) |
| AutoClass | no independent citation found in project docs — `Yu_2024_methods_review_260506.md` notes "the paper provides no algorithmic details / no package details given"; traced only to [Yu et al. 2024 review, DOI](https://doi.org/10.1186/s13059-024-03401-9) |
| deepMNN | [Luo et al. 2021, *Front Genet*, "deepMNN: Deep Learning-Based Single-Cell RNA Sequencing Data Batch Correction Using Mutual Nearest Neighbors"] — note: the in-code docstring/plan cites PMID 34616432, but PubMed resolves this paper to [PMID 34447413](https://pubmed.ncbi.nlm.nih.gov/34447413/); please verify before citing — no PyPI package; source only via GitHub `zoubin-ai/deepMNN` (repo existence not independently re-verified here) |
| iNMF | [PMID 26377073](https://pubmed.ncbi.nlm.nih.gov/26377073/) · maintained implementation: [GitHub `welch-lab/liger`](https://github.com/welch-lab/liger) |
| MultiBaC | [PMID 32131696](https://pubmed.ncbi.nlm.nih.gov/32131696/) |
| POIBM | [PMID 35199138](https://pubmed.ncbi.nlm.nih.gov/35199138/) |

### 3b. Requires matched/paired/bridge samples not present in the data (7)

| Tool | Link(s) |
|---|---|
| MatchMixeR | [Du et al. 2020, *Bioinformatics* 36(8):2486–2492, DOI](https://doi.org/10.1093/bioinformatics/btaa078) · [GitHub `dy16b/Cross-Platform-Normalization`](https://github.com/dy16b/Cross-Platform-Normalization) |
| COCONUT | [Sweeney, Wong & Khatri 2016, *Sci Transl Med* 8(346):346ra91, DOI](https://doi.org/10.1126/scitranslmed.aaf7165) · R package `COCONUT` on CRAN · [data/code, khatrilab.stanford.edu/sepsis](http://khatrilab.stanford.edu/sepsis) |
| ESLR | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318) |
| QN-CN (CrossNorm) | [Cheng et al. 2016, *Sci Rep* 6:18898] — no DOI recorded in project docs; code was MATLAB supplementary material only, no maintained package |
| Ratio-based (Quartet) | no independent citation found in project docs — traced only to [Yu et al. 2024 review, DOI](https://doi.org/10.1186/s13059-024-03401-9) |
| BRIDGE | [PMID 34905304](https://pubmed.ncbi.nlm.nih.gov/34905304/) |
| Remeasure | [PMID 38177326](https://pubmed.ncbi.nlm.nih.gov/38177326/) |

### 3c. Output is not a corrected expression matrix (5)

| Tool | Link(s) |
|---|---|
| UPC (Universal exPression Code) | [McCall et al. 2013, *PNAS*, "Multiplatform single-sample estimates of transcriptional activation," PMID 24128763](https://pubmed.ncbi.nlm.nih.gov/24128763/) · [Bioconductor `SCAN.UPC`](https://bioconductor.org/packages/SCAN.UPC) |
| QD (Quantile Discretization) | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318) |
| NorDi (Normalized Discretization) | same as QD — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318) |
| PLIDA | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318) |
| Divergence Analysis | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318) |

### 3d. Redundant with / inferior to / superseded by an adopted method (5)

| Tool | Link(s) |
|---|---|
| Rank-in | [Qiu, Wu & Hu 2013, *BMC Bioinformatics* 14:124, DOI](https://doi.org/10.1186/1471-2105-14-124) — same underlying paper as adopted `18_rank`; redundant by design |
| QNR (Robust Quantile Normalization) | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318); the review itself reports QNR performs worse than standard QN |
| Shambhala-1 | superseded by Shambhala-2; see [Borisov et al. 2022, DOI](https://doi.org/10.3390/biomedicines10092318) |
| QN-Z | not an independently published method — a pipeline variant studied within [Foltz, Greene & Taroni 2023, *Commun Biol* 6:222, DOI](https://doi.org/10.1038/s42003-023-04588-6) |
| RUV-2 | [Gagnon-Bartsch & Speed 2012, *Biostatistics* 13(3):539–552, DOI](https://doi.org/10.1093/biostatistics/kxr034) (project docs also list a second PMID, 25692814, for a related RUVSeq-family paper) |

### 3e. No maintained/accessible software at screening time (3)

| Tool | Link(s) |
|---|---|
| IBN (Integrative Bayesian Network) | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318); no public implementation ever located |
| DisTran (Distribution Transformation) | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318); described as a predecessor of FSQN |
| GQ (Gene Quantiles) | no independent citation found in project docs — traced only to [Borisov et al. 2022 review, DOI](https://doi.org/10.3390/biomedicines10092318) |

### 3f. Reported to actively harm signal (3)

| Tool | Link(s) |
|---|---|
| Z-scoring (standalone) | not an independently published method — discussed as a preprocessing step within [Foltz et al. 2023, DOI](https://doi.org/10.1038/s42003-023-04588-6) |
| BMC (Batch Mean-Centering) | no PMID recorded in the Yu 2024 supplementary table ("described as standard practice") — traced to [Yu et al. 2024 review, DOI](https://doi.org/10.1186/s13059-024-03401-9) |
| Z-scaled | same as BMC — standard practice, no PMID; traced to [Yu et al. 2024 review, DOI](https://doi.org/10.1186/s13059-024-03401-9) |

---

## 4. Rejected — Stage 2: post-implementation exclusion (8, code written and tried, then excluded)

These 8 are the same ones that explain why the registry is described as "31 methods (not 39)" in the top-level `CLAUDE.md`. Full detail already in `methods_table_for_manuscript.md`; links repeated here for completeness.

| Method | Registry key | Reason class | Link(s) |
|---|---|---|---|
| PEER | `24_peer_k10` | No maintained software | [Stegle, Parts, Piipari et al. 2012, *Nat Protoc* 7:500–507, DOI](https://doi.org/10.1038/nprot.2011.457) · original code (unmaintained for R≥4.5): [GitHub `PMBio/peer`](https://github.com/PMBio/peer) |
| exploBATCH | `36_explobatch` | No maintained software | [Nyamundanda, Gormley, Fan, Gallagher & Brennan 2017, *Sci Rep* 7:12869] (PMID 28883548) · [GitHub `syspremed/exploBATCH`](https://github.com/syspremed/exploBATCH) — hard dependency [GitHub `maxkuhn/fMM`](https://github.com/maxkuhn/fMM) is deleted (404) |
| deepMNN | `32_deepmnn` | Architecturally incompatible | see Stage-1 entry above (PMID discrepancy flagged) · [GitHub `zoubin-ai/deepMNN`](https://github.com/zoubin-ai/deepMNN) |
| DASC | `35_dasc` | Architecturally incompatible (wrong output type) | [Yi, Raman, Zhang, Allen & Liu 2018, *Bioinformatics* 34(7):1141–1147, PMID 29617963](https://pubmed.ncbi.nlm.nih.gov/29617963/) · [GitHub `zhanglabNKU/DASC`](https://github.com/zhanglabNKU/DASC) · [Bioconductor `DASC`](https://bioconductor.org/packages/DASC) |
| reComBat | `30_recombat` | Infra/deployment drift | see Adopted table entry above — code is correct, pod ConfigMap was never synced |
| FAbatch | `37_fabatch` | Infra/deployment drift | see Adopted table entry above — `cmake`/`bapred` never added to the pod manifest |
| Procrustes | `39_procrustes` | Infra/deployment drift | see Adopted table entry above — `git clone` step never added to the pod manifest |
| Shambhala-2 (registry entry) | `20_shambhala` | Unresolved | see Adopted table entry above — infra present, zero valid rows in latest metrics; needs re-run |

*(Note: reComBat, FAbatch, Procrustes, and Shambhala-2 appear in both §2 and §4 deliberately — the code-level implementation is correct and "adopted" in that sense, but the actual K8s pod deployment currently fails to produce valid output. See `methods_table_for_manuscript.md` for the full explanation.)*

---

## 5. Review papers cited throughout

| Review | Link |
|---|---|
| Borisov & Buzdin 2022 | [*Biomedicines* 10(9):2318, DOI](https://doi.org/10.3390/biomedicines10092318) |
| Foltz, Greene & Taroni 2023 | [*Commun Biol* 6:222, DOI](https://doi.org/10.1038/s42003-023-04588-6) |
| Yu, Mai, Zheng & Shi 2024 | [*Genome Biol* 25:254, DOI](https://doi.org/10.1186/s13059-024-03401-9) · [supplementary table (76-method catalog), PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC13059_2024_3401_MOESM1_ESM) — local copies at `harmonization-tools-research/13059_2024_3401_MOESM1_ESM.{xlsx,csv}` |

---

## 6. Not individually linked — screened at a catalog level only

35 additional method names appear only as one-line rows in the Yu et al. 2024 supplementary table (§5 above), with a blanket "not applicable" verdict by data-type mismatch and no individual discussion in the project's own notes:

- **Metabolomics/proteomics-only (11):** batchCorr, B-MIS, QC-RLSC, EigenMS, LIMBR, mixEMM, mvMISE, WaveICA, WaveICA 2.0, NormAE, RUV-random
- **scRNA-seq matrix-factorization (7):** cFIT, [LIGER](https://github.com/welch-lab/liger), RUV-III-NB, scMerge, scPLS, Seurat v2 (MultiCCA), ZINB-WaVE
- **scRNA-seq distance-neighborhood (10):** scMC, BATMAN, [BBKNN](https://github.com/Teichlab/bbknn), BEER, IMGG, iSMNN, SMNN, SSBER, [Seurat v3](https://github.com/satijalab/seurat), Seurat v4
- **scRNA-seq deep learning (7):** BERMUDA, CBA, Cell BLAST, MAT2, MMD-ResNet, [SAUCIE](https://github.com/KrishnaswamyLab/SAUCIE), scDML

These are all documented in the Yu 2024 supplementary spreadsheet itself (§5 link) rather than individually researched in this project's own notes, so no per-tool link is asserted beyond that source table.

---

## 7. Open items for Daniil to confirm before citing this document

1. `bench_shared.py`'s pyComBat docstring attributes the method to "Müller et al. 2023" — the actual paper is Behdenna, Colange, Haziza et al. 2023.
2. `bench_shared.py`'s DWD docstring cites "(Qing & Marron 2018)" for `DWDLargeR` — the package's actual citation is Lam, Marron, Sun & Toh (2018, arXiv:1604.05473).
3. `bench_shared.py`'s deepMNN docstring cites PMID 34616432 — PubMed resolves the matching paper to PMID 34447413.
4. The M-ComBat citation ambiguity flagged in `methods_table_for_manuscript.md` is now resolved: the "M-ComBat" name/description traces to the Yu et al. 2024 review, not to "Zhang X 2024" (which belongs to AMDBNorm).
5. Several Borisov-2022-screened methods (QD, NorDi, PLIDA, IBN, Rank-in [as distinct from the paper backing `18_rank`], ESLR, DisTran, GQ, QNR, Shambhala-1, Divergence Analysis) have no independent citation recorded anywhere in the project's notes — only the Borisov 2022 review paper itself. If any of these need a standalone citation for the dissertation, they should be individually re-researched from the Borisov 2022 reference list rather than cited via this document.
6. "Angel"'s code link (Stemformatics `s4m_pyramid` Bitbucket repo) was found via a general search, not confirmed against the paper's own Data Availability statement — verify before citing.
