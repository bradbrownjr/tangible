# Changelog

All notable changes to **Covet** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] — 2026-04-29 — Beta

First public beta. Feature set is complete enough for self-hosted use; the
v1.0 release will follow after a beta cycle of bug fixes and docs polish.

### Server

- FastAPI 0.115 / SQLAlchemy 2 / Alembic with SQLite, PostgreSQL and MySQL
  drivers selectable via `COVET_DATABASE_URL`.
- Auth: local username + Argon2 password, session cookies, opaque API
  tokens for non-browser clients. OIDC scaffolding present (provider config
  in env, full UI flow lands in 1.0).
- Collections, items, tags, contacts, loans, photos (multipart, dedupe by
  sha256, on-disk under `DATA_DIR/photos/<sha[0:2]>/<sha>`).
- Importers: CLZ Movies/Music/Games/Books/Comics, generic CSV with column
  mapping, Covet JSON backup. Exports: per-type CSV + unified, JSON backup.
- CRDT sync skeleton (Automerge document per item, append-only change log,
  snapshot compaction). Cross-language interop with `automerge-kt` and JS
  is verified by the test suite. Mobile push lands in 1.0.
- Hardening: `SecurityHeadersMiddleware` (CSP, X-Frame-Options, COOP/CORP,
  HSTS), slowapi rate limits (120/min global, 5/min on `/auth/login` and
  `/auth/register`), `OriginCsrfMiddleware` for cookie-auth POSTs.
- Observability: structlog access log, Prometheus `/metrics` with route
  templates, `/healthz` (liveness) + `/readyz` (DB ping).
- CLI: `covet backup <user> <out>`, `covet restore <user> <in>`,
  `covet version`, `covet bootstrap-admin`.

### Web

- SvelteKit 2.8 + Svelte 5 runes, adapter-static SPA served by FastAPI
  fallback in production.
- Login / registration, collections list + detail, item create / delete,
  import wizard (CLZ + CSV + JSON restore), settings page with API token
  management.
- Theme toggle: Light / Dark / System with no-FOUC pre-hydration script
  and per-mode `meta[name="theme-color"]`.

### Android

- Compose Material 3 / Hilt / Retrofit / Room scaffold (AGP 8.7.2,
  Kotlin 2.0.21, minSdk 26).
- Login (URL + credentials → API token in DataStore), collection list +
  detail, item create / delete, ML Kit barcode scanner with CameraX
  preview.
- Offline-first reads via Room cache; `WorkManager` `SyncWorker` refreshes
  every 15 minutes when connected.

### Packaging

- Multi-stage `Dockerfile`, multi-arch GHCR image
  (`ghcr.io/bradbrownjr/covet`) with non-root runtime, configurable
  `PUID`/`PGID`/`UMASK`, tini + gosu entrypoint.
- Compose examples for standard / Postgres / Unraid layouts.
- GitHub Actions: lint+tests for server / web, dependency audit
  (pip-audit + npm audit), Docker smoke test, multi-arch image
  release on tag, Android debug + release APK build (release signs
  when `ANDROID_KEYSTORE_BASE64` secret is set and a Release is published).

### Known limitations (deferred to 1.0)

- Item detail page, photo gallery and bulk-edit toolbar in the web UI
  are not yet implemented.
- Public share pages (`/s/<slug>`) route exists on the server but no UI.
- OIDC end-to-end flow not yet wired into the web login screen.
- Android offline writes are still synchronous; pending-op queue + CRDT
  push lands in 1.0.
- Photo capture / attach in the Android client.
