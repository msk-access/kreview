# Docker Guide

`kreview` is published as a Docker image to the GitHub Container Registry (GHCR) on every tagged release.

---

## Pulling the Image

```bash
docker pull ghcr.io/msk-access/kreview:latest
```

Or pin to a specific version:

```bash
docker pull ghcr.io/msk-access/kreview:latest
```

---

## Running with Docker

```bash
docker run --rm \
  -v /path/to/data:/app/data \
  -v /path/to/output:/app/results \
  ghcr.io/msk-access/kreview:latest \
  kreview run \
    --cancer-samplesheet /app/data/samplesheet.csv \
    --healthy-xs1-samplesheet /app/data/healthy_xs1.csv \
    --healthy-xs2-samplesheet /app/data/healthy_xs2.csv \
    --cbioportal-dir /app/data/cbioportal/ \
    --krewlyzer-dir /app/data/krewlyzer/ \
    --output /app/results/ \
    --workers 4
```

!!! tip "Volume Mounts"
    Mount your input data and output directories using `-v`. The container expects data at `/app/data` and writes results to `/app/results` by default.

---

## Dockerfile Architecture

The image uses a **multi-stage build** for minimal size:

```dockerfile
# Stage 1: Build the wheel
FROM python:3.12-slim as builder   # (1)!
WORKDIR /src
COPY . .
RUN pip install --upgrade pip build && python -m build --wheel

# Stage 2: Runtime (slim)
FROM python:3.12-slim              # (2)!
WORKDIR /app
COPY --from=builder /src/dist/*.whl /app/
RUN pip install --no-cache-dir /app/*.whl && rm /app/*.whl

# Install Quarto for dashboard rendering
RUN apt-get update && \            # (3)!
    wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.551/quarto-1.4.551-linux-amd64.deb && \
    dpkg -i quarto-*.deb && rm quarto-*.deb

RUN mkdir -p /app/data /app/results
CMD ["kreview", "--help"]
```

1. Builder stage compiles the wheel but is discarded from the final image
2. Runtime stage is a clean `python:3.12-slim` with only the installed package
3. Quarto is required for generating the interactive HTML Plotly dashboards

---

## GHCR Image Labels

Every image is annotated with OCI-standard metadata:

| Label | Value |
|-------|-------|
| `org.opencontainers.image.title` | `kreview` |
| `org.opencontainers.image.description` | Evaluate cfDNA fragmentomics features for ctDNA detection |
| `org.opencontainers.image.vendor` | MSK-ACCESS |
| `org.opencontainers.image.licenses` | AGPL-3.0 |
