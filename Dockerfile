# syntax=docker/dockerfile:1.7
#
# Multi-stage build for Tangible.
#
#   1. web-builder  — builds the SvelteKit static SPA
#   2. py-builder   — builds the Python wheel
#   3. runtime      — minimal image, non-root, configurable UID/GID
#
# Build:
#   docker build -t ghcr.io/bradbrownjr/tangible:dev .
# Run:
#   docker run --rm -p 8000:8000 -v $PWD/data:/data -v $PWD/config:/config \
#       ghcr.io/bradbrownjr/tangible:dev

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
    if [ -f package-lock.json ]; then npm ci --no-audit --no-fund --omit=optional; \
    else npm install --no-audit --no-fund --omit=optional; fi

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
COPY LICENSE NOTICE README.md CHANGELOG.md ./
COPY server/pyproject.toml ./server/pyproject.toml
COPY server/src ./server/src
COPY server/alembic.ini ./server/alembic.ini
COPY server/alembic ./server/alembic

# Build wheel + collect runtime dependencies into a venv we can copy across
RUN uv venv --python python${PYTHON_VERSION} /opt/tangible \
    && uv pip install --python /opt/tangible/bin/python --no-cache ./server \
    && mkdir -p /opt/tangible/share/tangible \
    && cp -r /src/server/alembic /opt/tangible/share/tangible/alembic \
    && cp /src/server/alembic.ini /opt/tangible/share/tangible/alembic.ini \
    && cp /src/CHANGELOG.md /opt/tangible/share/tangible/CHANGELOG.md

# ----------------------------------------------------------------------------
# Stage 3: runtime
# ----------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/tangible/bin:${PATH}" \
    TANGIBLE_DATA_DIR=/data \
    TANGIBLE_CONFIG_DIR=/config \
    TANGIBLE_WEB_DIR=/app/web \
    TANGIBLE_ALEMBIC_DIR=/opt/tangible/share/tangible/alembic \
    TANGIBLE_HOST=0.0.0.0 \
    TANGIBLE_PORT=8000 \
    PUID=1000 \
    PGID=1000 \
    UMASK=0022

# Tini for clean signal handling, gosu for safe step-down from root
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini gosu ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 tangible \
    && useradd  --system --uid 1000 --gid tangible --home-dir /app --shell /usr/sbin/nologin tangible \
    && mkdir -p /data /config /app/web

# Python venv with tangible + deps
COPY --from=py-builder /opt/tangible /opt/tangible

# SvelteKit static build (served by FastAPI)
COPY --from=web-builder /src/web/build /app/web

# Entrypoint
COPY docker/entrypoint.sh /usr/local/bin/tangible-entrypoint
RUN chmod +x /usr/local/bin/tangible-entrypoint

VOLUME ["/data", "/config"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:${TANGIBLE_PORT}/healthz || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/tangible-entrypoint"]
CMD ["serve"]

# OCI labels (populated by CI on tag builds)
ARG VCS_REF=
ARG BUILD_DATE=
ARG VERSION=dev
LABEL org.opencontainers.image.title="Tangible" \
      org.opencontainers.image.description="Self-hosted personal inventory management" \
      org.opencontainers.image.source="https://github.com/bradbrownjr/tangible" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.version="${VERSION}"
