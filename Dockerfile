# Stage 1: Build
FROM python:3.12-slim as builder

WORKDIR /src
COPY . .

# Install build dependencies and build wheel
RUN pip install --upgrade pip build && \
    python -m build --wheel

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Copy wheel from builder and install
COPY --from=builder /src/dist/*.whl /app/
RUN pip install --no-cache-dir /app/*.whl && \
    rm /app/*.whl

# Install Quarto natively for standalone dashboard rendering
RUN apt-get update && apt-get install -y wget && \
    wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.551/quarto-1.4.551-linux-amd64.deb && \
    dpkg -i quarto-1.4.551-linux-amd64.deb && \
    rm quarto-1.4.551-linux-amd64.deb && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure output directories exist
RUN mkdir -p /app/data /app/results

CMD ["kreview", "--help"]
