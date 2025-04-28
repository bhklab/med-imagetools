# ---------------------
# example build command:
# docker buildx \
#   --build-arg VERSION=0.1.0 \
#   --build-arg GIT_COMMIT=$(git rev-parse HEAD) \
#   --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
#   -t med-imagetools:latest \
#   -t med-imagetools:0.1.0 \
#   --platform linux/amd64,linux/arm64 \
#   --file Dockerfile 
# -----------------
# BUILD STAGE
# -----------------
ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim as builder

ARG VERSION
ARG GIT_COMMIT
ARG BUILD_DATE

# Install only minimal build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install your package
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir med-imagetools

# -----------------
# FINAL STAGE
# -----------------
FROM python:${PYTHON_VERSION}-slim

ARG VERSION
ARG GIT_COMMIT
ARG BUILD_DATE

LABEL maintainer="Benjamin Haibe-Kains" \
    license="MIT" \
    usage="docker run -it --rm <image_name> imgtools --help" \
    org.opencontainers.image.title="Med-ImageTools" \
    org.opencontainers.image.description="Tools for medical imaging analysis" \
    org.opencontainers.image.url="https://github.com/bhklab/med-imagetools" \
    org.opencontainers.image.source="https://github.com/bhklab/med-imagetools" \
    org.opencontainers.image.documentation="https://github.com/bhklab/med-imagetools/docs" \
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${GIT_COMMIT}" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.authors="Benjamin Haibe-Kains <your-email@example.com>"

# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION}/site-packages /usr/local/lib/python${PYTHON_VERSION}/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Check install (optional safety)
RUN imgtools --help

# Default command
CMD ["/bin/bash"]
