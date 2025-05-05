ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim

# Add uv binary from official release
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Use uv to install into system Python environment
ENV UV_SYSTEM_PYTHON=1
RUN uv pip install --system --pre --no-cache med-imagetools

# Metadata
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
    org.opencontainers.image.version="${VERSION}" \
    org.opencontainers.image.revision="${GIT_COMMIT}" \
    org.opencontainers.image.created="${BUILD_DATE}" \
    org.opencontainers.image.authors="Jermiah Joseph"

# Clean up all non-essential files
RUN rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Optional test
RUN imgtools --help

CMD ["/bin/bash"]