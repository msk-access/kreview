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

# Ensure output directories exist
RUN mkdir -p /app/data /app/results

CMD ["kreview", "--help"]
