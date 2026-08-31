FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        gnupg2 ca-certificates wget curl git \
        build-essential gfortran \
        libcurl4-openssl-dev libssl-dev libxml2-dev \
        libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
        libhdf5-dev libbz2-dev liblzma-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install R 4.5 from CRAN.
# Key fingerprint: 95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7 (Johannes Ranke / CRAN)
# Repo bookworm-cran40 ships R 4.5.x despite the "40" suffix in the name.
RUN curl -s "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x95C0FAF38DB3CCAD0C080A7BDC78B2DDEABC47B7" \
        | gpg --dearmor -o /usr/share/keyrings/r-project.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/r-project.gpg] \
        https://cloud.r-project.org/bin/linux/debian bookworm-cran40/" \
        > /etc/apt/sources.list.d/r-cran.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends r-base r-base-dev \
    && rm -rf /var/lib/apt/lists/*

COPY harmonization-scripts/install_r_packages.R /tmp/install_r_packages.R
RUN Rscript /tmp/install_r_packages.R

COPY harmonization-scripts/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY harmonization-scripts/ harmonization-scripts/

# WORKDIR must match cwd= in subprocess.run() inside run_cross_product_parallel.py
WORKDIR /app/harmonization-scripts

# No fixed ENTRYPOINT — pod stays alive so any script can be run via kubectl exec
# or VSCode Kubernetes extension. Override CMD for unattended batch runs:
#   command: ["python", "run_cross_product_parallel.py"]
#   args:    ["--n-workers", "6", "--skip-if-exists"]
CMD ["sleep", "infinity"]
