# =============================================================================
# kreview — Multi-target Dockerfile
#
# Targets:
#   cpu   → python:3.12-slim (~1.5 GB) — default, used by all CPU NF processes
#   gpu   → nvidia/cuda:12.4 + Python 3.12 (~8–10 GB) — used by process_gpu
#
# Build:
#   docker build --target cpu -t ghcr.io/msk-access/kreview:vX.Y.Z .
#   docker build --target gpu -t ghcr.io/msk-access/kreview:vX.Y.Z-gpu .
# =============================================================================

# ── Stage 1: Builder (shared across both targets) ────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /src

# Copy only what's needed for the wheel build.
# LICENSE is required — pyproject.toml references it for dist-info embedding.
# nbs/ is NOT needed — kreview/ already contains the exported Python modules.
COPY pyproject.toml settings.ini README.md LICENSE ./
COPY kreview/ kreview/

# Build the kreview wheel (used by both cpu and gpu targets)
RUN pip install --no-cache-dir --upgrade pip build && \
    python -m build --wheel

# ── Stage 2a: CPU Runtime ────────────────────────────────────────────────────
FROM python:3.12-slim AS cpu

LABEL org.opencontainers.image.title="kreview" \
      org.opencontainers.image.description="kreview — CPU runtime for fragmentomics evaluation" \
      org.opencontainers.image.url="https://github.com/msk-access/kreview" \
      org.opencontainers.image.source="https://github.com/msk-access/kreview" \
      org.opencontainers.image.vendor="MSK-ACCESS" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.authors="Ronak Shah <shahr2@mskcc.org>"

WORKDIR /app

# Copy wheel from builder and install (CPU-only, no GPU extras)
COPY --from=builder /src/dist/*.whl /app/
RUN pip install --no-cache-dir /app/*.whl && \
    rm /app/*.whl

# Install runtime essentials (procps, bash) for Nextflow compatibility
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install -y --no-install-recommends \
    procps bash tzdata && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure output directories exist
RUN mkdir -p /app/data /app/results

ENTRYPOINT ["kreview"]
CMD ["--help"]

# ── Stage 2b: GPU Runtime (CUDA 12.4, supports A100/A40/H100/L40S) ──────────
FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04 AS gpu

LABEL org.opencontainers.image.title="kreview-gpu" \
      org.opencontainers.image.description="kreview — GPU runtime (CUDA 12.4, torch, tabpfn, tabicl)" \
      org.opencontainers.image.url="https://github.com/msk-access/kreview" \
      org.opencontainers.image.source="https://github.com/msk-access/kreview" \
      org.opencontainers.image.vendor="MSK-ACCESS" \
      org.opencontainers.image.licenses="AGPL-3.0" \
      org.opencontainers.image.authors="Ronak Shah <shahr2@mskcc.org>"

# Install Python 3.12 runtime (no -dev headers — not needed at runtime).
# If a transitive dep ever ships only an sdist, this will fail; all current
# GPU deps have cp312 wheels so this is safe today.
# deadsnakes PPA provides Python 3.12 for Ubuntu 22.04.
RUN export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common tzdata && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv \
    procps bash curl && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    # Clean up packages only needed for setup
    apt-get remove -y software-properties-common curl && \
    apt-get autoremove -y && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install kreview with GPU extras from the local wheel.
# Apply the [gpu] extra directly to the wheel file path to ensure pip
# resolves it locally rather than pulling kreview from PyPI.
# Note: torch 2.x pip wheels bundle their own CUDA runtime as nvidia-*
# pip packages regardless of --index-url, so the GPU image is ~8-10 GB.
# The CI disk-space issue is solved by jlumbroso/free-disk-space in the
# workflow, not by image-size tricks.
COPY --from=builder /src/dist/*.whl /app/
RUN WHL="$(ls /app/*.whl)" && \
    pip3 install --no-cache-dir "${WHL}[gpu]" && \
    rm /app/*.whl

# Ensure output directories exist
RUN mkdir -p /app/data /app/results

ENTRYPOINT ["kreview"]
CMD ["--help"]
