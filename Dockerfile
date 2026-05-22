# =============================================================================
# kreview — Multi-target Dockerfile
#
# Targets:
#   cpu   → python:3.12-slim (~2 GB) — default, used by all CPU NF processes
#   gpu   → nvidia/cuda:12.4 + Python 3.12 (~8-10 GB) — used by process_gpu
#
# Build:
#   docker build --target cpu -t ghcr.io/msk-access/kreview:vX.Y.Z .
#   docker build --target gpu -t ghcr.io/msk-access/kreview:vX.Y.Z-gpu .
# =============================================================================

# ── Stage 1: Builder (shared across both targets) ────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /src
COPY . .

# Build the kreview wheel (used by both cpu and gpu targets)
RUN pip install --upgrade pip build && \
    python -m build --wheel

# ── Stage 2a: CPU Runtime ────────────────────────────────────────────────────
FROM python:3.12-slim AS cpu

# OCI Labels for GitHub Container Registry
LABEL org.opencontainers.image.title="kreview"
LABEL org.opencontainers.image.description="kreview — CPU runtime for fragmentomics evaluation"
LABEL org.opencontainers.image.url="https://github.com/msk-access/kreview"
LABEL org.opencontainers.image.source="https://github.com/msk-access/kreview"
LABEL org.opencontainers.image.vendor="MSK-ACCESS"
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.authors="Ronak Shah <shahr2@mskcc.org>"

WORKDIR /app

# Copy wheel from builder and install (CPU-only, no GPU extras)
COPY --from=builder /src/dist/*.whl /app/
RUN pip install --no-cache-dir /app/*.whl && \
    rm /app/*.whl

# Install runtime essentials (procps, bash) for Nextflow compatibility & Quarto natively
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget procps bash && \
    wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.551/quarto-1.4.551-linux-amd64.deb && \
    dpkg -i quarto-1.4.551-linux-amd64.deb && \
    rm quarto-1.4.551-linux-amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure output directories exist
RUN mkdir -p /app/data /app/results

ENTRYPOINT ["kreview"]
CMD ["--help"]

# ── Stage 2b: GPU Runtime (CUDA 12.4, supports A100/A40/H100/L40S) ──────────
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS gpu

# OCI Labels for GitHub Container Registry
LABEL org.opencontainers.image.title="kreview-gpu"
LABEL org.opencontainers.image.description="kreview — GPU runtime (CUDA 12.4, torch, tabpfn, tabicl)"
LABEL org.opencontainers.image.url="https://github.com/msk-access/kreview"
LABEL org.opencontainers.image.source="https://github.com/msk-access/kreview"
LABEL org.opencontainers.image.vendor="MSK-ACCESS"
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.authors="Ronak Shah <shahr2@mskcc.org>"

# Install Python 3.12 + pip on the CUDA Ubuntu base
# deadsnakes PPA provides Python 3.12 for Ubuntu 22.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev \
    wget procps bash curl && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Two-step install: base wheel first, then GPU extras (torch, tabpfn, tabicl).
# This avoids shell glob + pip extras bracket quoting issues.
COPY --from=builder /src/dist/*.whl /app/
RUN pip3 install --no-cache-dir /app/*.whl && \
    pip3 install --no-cache-dir "kreview[gpu]" && \
    rm /app/*.whl

# Install Quarto for report generation
RUN wget -q https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.551/quarto-1.4.551-linux-amd64.deb && \
    dpkg -i quarto-1.4.551-linux-amd64.deb && \
    rm quarto-1.4.551-linux-amd64.deb

# Ensure output directories exist
RUN mkdir -p /app/data /app/results

ENTRYPOINT ["kreview"]
CMD ["--help"]
