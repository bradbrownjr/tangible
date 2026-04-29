# Changelog

All notable changes to **Covet** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Document attachments + expiry tracking** — items can now hold
  arbitrary file attachments (manuals, receipts, warranties). New
  endpoints `POST/GET /items/{id}/documents`, `GET /documents/{id}/download`,
  `PATCH/DELETE /documents/{id}`. Files are content-addressed by SHA-256
  under `documents_dir` (default `data/documents`), de-duplicated across
  items, and capped at 50 MB by default. Each document carries
  `label`, `category` (`manual`/`receipt`/`warranty`/...), and an
  optional `expires_at`. Items themselves also gain `expires_at`. New
  `GET /expiring?within_days=N` dashboard endpoint surfaces all items
  and documents whose expiry falls within the window, scoped to
  collections the user can read.

- **URL metadata scraper** — new `POST /metadata/scrape {url}` endpoint
  fetches a URL through a pluggable adapter registry and returns
  suggested item fields (`title`, `description`, `image_url`,
  `item_type`, `attrs`). Ships with an Open Library ISBN adapter and a
  generic OpenGraph fallback that parses `og:*`, `<meta name="...">`
  and `<title>`. SSRF-protected: rejects non-http(s) URLs and any host
  that resolves to a private/loopback/link-local address. Web app gets
  a "Scrape URL" prefill on the new-item form. Adapters for IGDB / IMDB
  / Discogs can be registered via `register_adapter()`.

- **Item templates / per-type custom fields** — collections gain
  reusable `ItemTemplate` schemas (`name`, `item_type`, `fields[]`).
  Each field declares `key`, `label`, `type`
  (`text|number|boolean|date|url|select`), optional `required`,
  `default` and `options`. Items can attach `template_id`; on
  create/update the server validates and coerces `attrs` against the
  template's fields (rejects missing required, applies defaults,
  enforces `select` options). New endpoints
  `/collections/{id}/templates` (CRUD) and `/templates/{id}` plus a web
  Templates page linked from the collection.

## [0.10.0] — 2026-04-29 — Make it shareable

### Added

- **OIDC / OAuth2 SSO (server)** — admin can configure one or more OIDC
  providers via `oidc_providers:` in `covet.yaml`. New endpoints
  `/auth/oidc/{provider}/login` and `/auth/oidc/{provider}/callback`
  perform the full authorization-code flow via Authlib, then mint a
  Covet session cookie. First login creates a user (or links to an
  existing one by email). Optional `admin_groups` claim mapping promotes
  members of named groups to admin. `/config/public` now lists enabled
  providers so the web sign-in page renders the right buttons.
- **Members panel** — collection owners can now invite existing users to
  a collection as `editor` or `viewer` via
  `GET/POST/PATCH/DELETE /collections/{id}/members`. Web app gains a
  per-collection Members page with add/remove/role-change controls.
  Owner is surfaced in the member list (read-only).
- **Public read-only share links** — owners can mint per-collection
  share URLs (`/collections/{id}/share-links` CRUD). Anonymous visitors
  load `/public/share/{slug}` (collection metadata) and
  `/public/share/{slug}/items` to browse the collection — no sign-in
  required. Links can have an optional label and `expires_at`; revoke
  immediately cuts off access. Web app exposes the share UI on the
  Members page and serves the public viewer at `/share/{slug}`.
- **Single-use invitation tokens** — owners create
  `/collections/{id}/invitations` to mint a one-time link
  (`/invite/{token}` in the web app). The plaintext token is shown only
  once at creation; the server stores the SHA-256 hash. Invitees preview
  the invitation anonymously, then sign in (or sign up) to accept,
  becoming a member at the chosen role. Acceptance never downgrades an
  existing higher role.
- **Append-only audit log** — new `audit_log` table records membership,
  share-link and invitation events (`member.add/update_role/remove`,
  `share_link.create/revoke`, `invitation.create/revoke/accept`) with
  actor, collection, target and JSON payload. New `GET /audit` endpoint:
  global view requires admin; per-collection view (`?collection_id=`)
  requires owner. Web Members page surfaces the recent activity log for
  the collection.

### Changed

- `OIDCProvider` config moved off `BaseSettings` (it's nested config, not
  env-driven) so YAML overlay works correctly.

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
