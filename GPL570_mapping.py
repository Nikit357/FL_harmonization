from tqdm import tqdm
import pyreadr
from biomart import BiomartServer
import pandas as pd
import io

result = pyreadr.read_r("DLBCL_selected_samples.Rdata")  # also works for Rds

# 1. Connect to Ensembl BioMart
server = BiomartServer("http://www.ensembl.org/biomart")
mart = server.datasets["hsapiens_gene_ensembl"]

# 2. Define your list of probe IDs
probe_ids = result["indata"].index.to_list()
mapping_list = []

for i in tqdm(range(0,len(probe_ids) // 100)):
    if i != (len(probe_ids) // 100) - 1:
        probe_ids_local = probe_ids[i*100:(i+1)*100]
    else:
        probe_ids_local = probe_ids[i*100:]
    # 3. Query the mapping
    response = mart.search(
        {
            "filters": {"affy_hg_u133_plus_2": probe_ids_local},
            "attributes": ["affy_hg_u133_plus_2", "hgnc_symbol", "entrezgene_id"],
        }
    )

    # 4. Convert to DataFrame
    probes_mapping = pd.read_csv(
        io.StringIO(response.text),
        sep="\t",
        header=None,
        names=["ProbeID", "HGNC", "Entrez"],
    )
    mapping_list.append(probes_mapping)
#    print(len(probes_mapping))
probes_mapping_all = pd.concat(mapping_list)
probes_mapping_all.to_csv('GPL570_mapping_probes.csv')
