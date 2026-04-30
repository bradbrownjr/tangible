# Changelog

All notable changes to **Covet** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.14.0] — 2026-04-30

### Added

- **Grid view for collections (web).** A toggle button in the collection
  detail filter bar switches between the existing list/table view and a
  tiled card grid. Each card shows the creator, title, series/subtitle,
  condition, and category badge at a glance. The chosen view persists in
  `localStorage`.
- **Pull to refresh (Android).** Swipe down on the collection item list to
  immediately sync the latest items from the server without waiting for the
  background sync worker.
- **Creator and subtitle fields when adding items (web).** The add-item
  form now shows a context-aware creator field (Artist/Band, Author,
  Director, Developer, or Designer depending on category) and a
  Series/subtitle field for books, movies, and games. Enter in each field
  moves focus to the next, and after adding an item focus returns to the
  first field for rapid bulk entry.
- **Inline item editing (web).** Items can now be edited directly in the
  list and grid views without navigating away. An Edit button per row
  expands an inline form for title, creator, series/subtitle, condition,
  and quantity.
- **Template editing and cloning (web).** The Templates tab now has per-row
  Edit and Clone buttons (editor/owner only). Edit expands an inline field
  builder. Clone duplicates the template within the same collection.
- **Role-gated web UI.** The server now returns `my_role` on every
  collection response. Viewers see the collection read-only (no Add, Edit,
  or Delete buttons). Editors can add, edit, and delete items and templates.
  The Delete collection button is owner-only.

## [0.13.4] — 2026-04-29

### Fixed

- **Android APK now ships with GitHub Releases.** A compilation error
  (`WizardStep` private enum exposed through public data class) and a
  workflow path bug (rename step ran from wrong directory) both
  prevented the APK from being attached to prior releases.

## [0.13.3] — 2026-05-01

### Fixed

- **Android app now works with the v0.13.0 taxonomy changes.** The app
  was sending `type` on every new item (e.g. `"movie"`), which the
  server rejected with 422 since v0.13.0 removed the old enum in favour
  of the categories table. Items can now be added again.
- **Android: category picker replaces free-text type field.** The
  add-item dialog now shows cascading Root → Sub-category dropdowns
  loaded from the server, pre-selected to the collection's default
  category.
- **Android: barcode scanner wired to item creation.** Scanning a
  barcode (e.g. an ISBN or EAN) from the collection detail screen now
  calls the metadata scrape endpoint to prefill the item title and
  category before you tap Add.
- **Android: collection creation wizard.** Tapping + on the collections
  screen now opens a category-preset picker (Books, Music, Movies…)
  followed by a name / description form — matching the web experience.
- **Android: Room database schema updated to v2** (destructive
  migration — local cache is rebuilt on first launch after update).

## [0.13.2] — 2026-04-30

### Changed

- **Cleaner collection navigation.** The arrow links
  (`Manage members →`, `Item templates →`, `Delete collection`) are
  replaced by a real button bar at the top of every collection page:
  **Items │ Templates │ Members │ Delete**. The same bar appears on
  the Templates and Members sub-pages with the active tab highlighted,
  so it's always obvious where you are.
- **Smarter add-item input.** The separate "Paste URL" and "Title"
  fields are merged into one input that detects what you typed:
  - Starts with `http://`/`https://` → scrape the page.
  - Looks like an ISBN-10, ISBN-13, or 12/13-digit EAN → look up via
    Open Library, prefilling title and category.
  - Anything else → use as the item title.
  The original ISBN/EAN is also stored on the item's `identifiers`.
- **Collection-aware search and filter.** Inside a preset collection
  (Music, Movies, etc.) the redundant **All categories** filter is
  hidden; the search box is labelled
  *"Search this collection (title)…"* so it's clear what it does.
- **Templates editor without JSON.** The Templates page now hides the
  category select (templates inherit the collection's default category)
  and ships a row builder for custom fields with key, label, type,
  required, and select options. An **Advanced (JSON)** toggle is still
  available for power users.

## [0.13.1] — 2026-04-30

### Added

- **Guided collection wizard.** The home page no longer presents a blank
  name field. Click **+ New collection** to pick a starting point
  (Music, Movies, Video Games, Tabletop, Books, Collectibles, Tools,
  Spices, or **Custom**). The chosen preset prefills the name and
  description and is stored on the collection so the new-item form on
  that collection's page defaults to the matching category root.
- **Delete a collection from the UI.** A **Delete collection** action
  is now available next to the Members and Templates links on the
  collection detail page; it confirms, calls
  `DELETE /collections/{id}`, and returns to the home list.
- **`collections.default_category_slug`** column (alembic 0009) +
  `default_category_slug` field on `CollectionCreate`/`CollectionUpdate`/
  `CollectionRead`. Optional and ignored when null — it is purely a UX
  hint for the create-item form.
## [0.13.0] — 2026-04-30

### Added

- **Hierarchical category taxonomy.** ~40 curated categories grouped
  under nine roots — Music, Movies, Video Games, Tabletop, Books,
  Collectibles, Tools, Spices, Other — replace the old flat item-type
  list. Cascading root → leaf selects appear on the new-item form,
  template editor, and CSV / list import wizards.
- **`GET /categories` endpoint.** Returns the seeded catalog so clients
  can render the picker without hardcoding values.
- **Subtree filtering.** `GET /items?category=<slug>` filters by exact
  leaf; `?category_subtree=<root>` filters by an entire root and all
  its leaves (e.g. show every "Music" item).
- **Per-category CSV templates.** The CSV import "Download template"
  button now downloads by category slug
  (`?category=movies.dvd`, `?category=music.vinyl`, …).

### Changed

- **Breaking:** the `ItemType` enum is gone. Items now carry a
  `category_id` foreign key (or accept a `category` slug on create);
  templates use `category_slug`; importers use `category_slug`; the
  metadata scraper returns `category` instead of `item_type`.
  Existing databases must be reset — there is no migration path from
  the old enum to the new categories table for the small number of
  pre-0.13 installations.

## [0.12.0] — 2026-04-29

### Added

- **In-app "What's new" modal.** A sparkle icon next to the version in
  the header opens a dialog rendering the project `CHANGELOG.md`
  directly. A small dot indicator highlights the button until you
  open it after a version bump.
- **Editable profile.** Click your name in the header to edit your
  display name, email, and password. A new `PATCH /auth/me` endpoint
  backs the form; admin-only fields (`is_admin`, `is_active`) are
  ignored on this route to prevent self-escalation.
- **Display name on registration.** The signup form now accepts an
  optional full name. When set, it is shown throughout the UI in
  place of the username (which stays your private login handle).
- **List import.** A new "List of titles" mode on the Import page
  accepts a pasted block of titles or a `.txt` upload and creates
  one item per non-blank line. Backed by `POST /imports/list`.
- **Downloadable CSV template.** The CSV import mode now offers a
  "Download template" button per item type, served from
  `GET /imports/csv/template?item_type=...`.
- **Debug APK attached to GitHub Releases.** Until a signing keystore
  is configured, the Android workflow now uploads the unsigned debug
  APK to each release as `covet-<version>-debug.apk`.

### Fixed

- **Same-origin POSTs no longer return 403.** The CSRF middleware
  treated `*` in `COVET_ALLOWED_HOSTS` as a literal hostname and
  rejected requests whose `Origin` host matched the request host.
  Both cases are now allowed.
- **Web UI no longer renders a blank page under the default CSP.** The
  hardening middleware shipped `script-src 'self'`, which silently
  blocked SvelteKit's inline bootstrap script and our pre-hydration
  theme script in `app.html`. Both inline blocks are now hashed at
  startup and added to `script-src` (`'sha256-...'`) so the SPA
  hydrates while the CSP stays strict — no `'unsafe-inline'`.
- **Unraid compose no longer requires a pre-existing `proxy` network.**
  The `docker-compose.unraid.yml` sample previously declared its
  network as `external: true`, which failed on a fresh box with
  `network proxy declared as external, but could not be found`. The
  network is now a Compose-managed bridge by default; instructions
  for switching to an external proxy network are inline in the file.
- **Default `COVET_ALLOWED_HOSTS` for the Unraid sample is now `*`.**
  The previous example assumed the user already had a public hostname
  + reverse proxy and would lock out plain LAN access at
  `http://<unraid-ip>:8000/`. The proxy hostname is now opt-in via
  `COVET_PUBLIC_URL` / `COVET_BEHIND_PROXY` overrides.

### Changed

- **First registered user is auto-promoted to admin.** When the database
  contains zero users, `POST /auth/register` always succeeds and the new
  account is created with `is_admin=true`, regardless of the
  `COVET_REGISTRATION_ENABLED` setting. After that initial signup the
  normal registration gate applies. This removes the need to set
  `COVET_ADMIN_USERNAME` / `COVET_ADMIN_PASSWORD` for casual deployments
  and matches the standard self-hosted-app pattern.

## [0.11.0] — 2026-04-29 — Make items richer

### Added

- **Photos API + multi-upload + URL ingest + HEIC/EXIF** — first-class
  HTTP endpoints for item photos:
  `POST /items/{id}/photos` (multipart, **multiple files** in one
  request),
  `POST /items/{id}/photos/from-url {url}` (server fetches the URL
  through the same SSRF guard used by the metadata scraper),
  `GET /items/{id}/photos`, `GET /photos/{id}/download`,
  `PATCH /photos/{id}` (set `sort_order`, set `is_primary`),
  `DELETE /photos/{id}` (auto-promotes the next photo to primary).
  Pillow + `pillow-heif` decode HEIF/HEIC and transcode to JPEG, and
  EXIF orientation is applied so saved pixels are upright (no more
  side-ways photos from iOS uploads). Photos are content-addressed by
  SHA-256 under `photos_dir` and de-duplicated. New `photos.is_primary`
  column (migration 0007).

- **Maintenance schedules** — items can carry recurring maintenance
  tasks (oil change, filter swap, calibration). New
  `MaintenanceTask` model + endpoints
  `POST/GET /items/{id}/maintenance`,
  `PATCH/DELETE /maintenance/{id}`,
  `POST /maintenance/{id}/complete` (advances `last_completed_at` and
  re-computes `next_due_at` from `interval_days`), and
  `GET /maintenance?within_days=N` for a due-soon dashboard scoped to
  readable collections.

- **Parent / child items (kits)** — items gain optional `parent_id`
  for grouping (a "Camera kit" with lens + body + battery as
  children). New `GET /items/{id}/children` endpoint. Server validates
  parent exists, lives in the same collection, is not the item itself,
  and that the assignment doesn't create a cycle.

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
