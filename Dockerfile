# Stage 1: Build
FROM python:3.12-slim as builder

WORKDIR /src
COPY . .

# Install build dependencies and build wheel
RUN pip install --upgrade pip build && \
    python -m build --wheel

# Stage 2: Runtime
FROM python:3.12-slim

# OCI Labels for GitHub Container Registry
LABEL org.opencontainers.image.title="kreview"
LABEL org.opencontainers.image.description="Evaluation Framework for Fragmentomics Features"
LABEL org.opencontainers.image.url="https://github.com/msk-access/kreview"
LABEL org.opencontainers.image.source="https://github.com/msk-access/kreview"
LABEL org.opencontainers.image.vendor="MSK-ACCESS"
LABEL org.opencontainers.image.licenses="AGPL-3.0"
LABEL org.opencontainers.image.authors="Ronak Shah <shahr2@mskcc.org>"

WORKDIR /app

# Copy wheel from builder and install
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
