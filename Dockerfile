# syntax=docker/dockerfile:1.7
#
# Multi-stage build for Covet.
#
#   1. web-builder  — builds the SvelteKit static SPA
#   2. py-builder   — builds the Python wheel
#   3. runtime      — minimal image, non-root, configurable UID/GID
#
# Build:
#   docker build -t ghcr.io/bradbrownjr/covet:dev .
# Run:
#   docker run --rm -p 8000:8000 -v $PWD/data:/data -v $PWD/config:/config \
#       ghcr.io/bradbrownjr/covet:dev

ARG PYTHON_VERSION=3.12
ARG NODE_VERSION=22
ARG UV_VERSION=0.5.4

# ----------------------------------------------------------------------------
# Stage 1: build the web SPA
# ----------------------------------------------------------------------------
FROM node:${NODE_VERSION}-alpine AS web-builder
WORKDIR /src/web

COPY web/package.json web/package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi

COPY web/ ./
RUN npm run build

# ----------------------------------------------------------------------------
# Stage 2: build the Python wheel
# ----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS py-builder
ARG UV_VERSION

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1

RUN pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /src
COPY LICENSE NOTICE README.md ./
COPY server/pyproject.toml ./server/pyproject.toml
COPY server/src ./server/src
COPY server/alembic.ini ./server/alembic.ini
COPY server/alembic ./server/alembic

# Build wheel + collect runtime dependencies into a venv we can copy across
RUN uv venv --python python${PYTHON_VERSION} /opt/covet \
    && uv pip install --python /opt/covet/bin/python --no-cache ./server \
    && mkdir -p /opt/covet/share/covet \
    && cp -r /src/server/alembic /opt/covet/share/covet/alembic \
    && cp /src/server/alembic.ini /opt/covet/share/covet/alembic.ini

# ----------------------------------------------------------------------------
# Stage 3: runtime
# ----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/covet/bin:${PATH}" \
    COVET_DATA_DIR=/data \
    COVET_CONFIG_DIR=/config \
    COVET_WEB_DIR=/app/web \
    COVET_ALEMBIC_DIR=/opt/covet/share/covet/alembic \
    COVET_HOST=0.0.0.0 \
    COVET_PORT=8000 \
    PUID=1000 \
    PGID=1000 \
    UMASK=0022

# Tini for clean signal handling, gosu for safe step-down from root
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini gosu ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 covet \
    && useradd  --system --uid 1000 --gid covet --home-dir /app --shell /usr/sbin/nologin covet \
    && mkdir -p /data /config /app/web

# Python venv with covet + deps
COPY --from=py-builder /opt/covet /opt/covet

# SvelteKit static build (served by FastAPI)
COPY --from=web-builder /src/web/build /app/web

# Entrypoint
COPY docker/entrypoint.sh /usr/local/bin/covet-entrypoint
RUN chmod +x /usr/local/bin/covet-entrypoint

VOLUME ["/data", "/config"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${COVET_PORT}/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/covet-entrypoint"]
CMD ["serve"]

# OCI labels (populated by CI on tag builds)
ARG VCS_REF=
ARG BUILD_DATE=
ARG VERSION=dev
LABEL org.opencontainers.image.title="Covet" \
      org.opencontainers.image.description="Self-hosted personal inventory management" \
      org.opencontainers.image.source="https://github.com/bradbrownjr/covet" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"
