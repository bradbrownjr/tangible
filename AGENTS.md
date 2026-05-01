# Agent Guide for Covet

This file is the persistent shared memory for any AI assistant working on
Covet (GitHub Copilot, Claude, etc.). It captures the rules of engagement,
project-specific gotchas, and a registry of every shipped feature so that
large refactors don't silently regress them.

---

## Always / Never Memory Protocol

- If the user says **"always"**, **"never"**, **"remember"**, **"don't"** or
  similar, treat it as a permanent project rule and add it here as a clear,
  testable directive.
- If a rule is not written down in this file, assume it will be forgotten in
  the next session.
- Update / remove rules that turn out to be wrong or outdated rather than
  letting them accumulate.

## Communication Style

- Be brief. Target 1–3 sentences for simple answers.
- Action over explanation — show the change, don't narrate "I'll now…".
- No preambles, no restating the user's request, no apologies for prior
  iterations. Just fix it.
- DRY / KISS / progressive cleanup — remove dead imports / commented blocks
  as you iterate.
- Parallel tool calls when operations are independent.
- For straightforward single-file changes, proceed directly. For large or
  cross-cutting changes, present a plan + open questions + risks first and
  get alignment before writing code.
- Treat every user question as requiring a direct answer; do not silently
  skip questions to start coding.

## Root-Cause Policy

- Never patch symptoms. Identify the underlying cause before fixing.
- Trace the call chain / data flow far enough to understand *why*, not just
  *where*.
- Prefer invasive-but-correct fixes over safe-but-superficial workarounds.
- After a fix, verify the symptom *and* the root cause are gone.

## Regression Check Policy

This is the bar that protects shipped features:

- **Before every commit**, mentally run `git diff --stat`. If deletions
  outnumber additions, or any single file is shrinking by more than ~50
  lines, **explicitly audit** that no shipped behavior is being removed.
- A single commit removing **200+ lines** from one file requires a written
  justification in the commit body (what was removed, why it is safe).
- Before any large file rewrite, list the named features / API routes /
  exported functions present in that file, then confirm each one survives
  the rewrite. Cross-reference against the Feature Registry below.
- Run the full local test suite after any multi-file change or any deletion
  of a non-trivial block:
  - Server: `cd server && uv run ruff check . && uv run pytest -q`
  - Web: `cd web && npm run check && npm run build`
  - Android is CI-only in this dev environment (no JDK locally).
- After pushing, watch the CI run. A regression that goes green locally but
  red in CI is still a regression — fix forward, don't disable the check.

## Commit & Release Policy

- Imperative mood; the body explains *what* changed and *why*.
- One logical change per commit. Don't batch unrelated work.
- Never commit broken builds, failing tests, or unresolved lint errors.
- After each major feature or bug fix, commit and push once local validation passes (`git add -A && git commit && git push`).
- The user does not currently use the `Co-authored-by: Copilot` trailer.
  Don't add it unless asked.
- Do not publish a new Docker image, tag a release, or publish an APK/GitHub Release artifact until the user explicitly says they are ready.

### Release procedure

A new version requires four file edits, one CHANGELOG entry, and a tag
push. The `release.yml` workflow auto-publishes the GitHub Release from the
tag and the matching `## [X.Y.Z]` section of `CHANGELOG.md`.

1. Bump version in:
   - `server/src/covet/__init__.py` (`__version__`)
   - `server/pyproject.toml` (`version`)
   - `web/package.json` (`"version"`)
   - `android/app/build.gradle.kts` (`versionCode` + `versionName`)
2. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md` describing the
   release in user-facing terms.
3. Commit, push, then `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`.
4. `release.yml` creates the GitHub Release. `release-image.yml` builds the
  multi-arch GHCR image at `:X.Y.Z`, `:X.Y`, `:X`. `android.yml` now runs on
  PRs, version tags, or manual dispatch only (not every push to `main`);
  signed APK upload requires `ANDROID_KEYSTORE_BASE64` etc. and is currently
  disabled until the user explicitly wants a release.

## Definition of Done

- Solves the validated root cause.
- Code is DRY / KISS, with no dead imports or commented-out blocks.
- Test suite passes locally for the affected component.
- `ruff check` / `svelte-check` / lint clean.
- Documentation updated (`CHANGELOG.md` for user-facing changes;
  `AGENTS.md` for new rules / gotchas; `README.md` only when needed).
- Update the user/admin guides whenever shipped behavior changes:
  `docs/user-guide.md` for web/server user workflows,
  `docs/android-user-guide.md` for Android workflows,
  `docs/admin-guide.md` for operator-facing behavior/config/upgrade notes.
  User/admin-facing features are not done until the relevant guides are caught up.
- **`CHANGELOG.md` is the source for the in-app "What's new" modal** —
  every user-facing change must land in `CHANGELOG.md` under
  `## [Unreleased]` (or the active version). The web client fetches
  `/changelog` and renders it; an out-of-date CHANGELOG ships
  out-of-date release notes to every user. Keep entries terse and
  user-oriented (no internal refactor noise).
- Committed and pushed; CI green on `main`.

## Phase Completion Guardrail ⚠️

**CRITICAL: Never change a phase from "in progress" to "✅ COMPLETE" without explicit audit:**

1. **Read the full ROADMAP section** for the phase top-to-bottom.
2. **Check for "pending", "planned", or "deferred"** — If any requirements remain in those states, the phase is NOT complete.
3. **Verify implementation** — For each listed requirement, confirm:
   - Code exists and is in the repo
   - Tests pass locally (`pytest`, `npm run check`, etc.)
   - ROADMAP, CHANGELOG, and code descriptions match
4. **Before marking done, ask the user:** "Ready to mark Phase X complete?" rather than auto-completing. This is a checkpoint to prevent premature closure (happens too easily with large multi-part phases).
5. **If in doubt, stop short** — Leave the phase "in progress" and summarize what's done vs. pending. The user will clarify scope.

This is a learned rule: Phase 10 and early Phase 11 were marked complete prematurely, causing wasted tokens on audit and rework. The guardrail prevents repeating that pattern.

---

## Project Layout

```
covet/
├── server/              # FastAPI + SQLAlchemy + Alembic (Python 3.12, uv, ruff, pytest)
│   ├── src/covet/
│   │   ├── api/         # Routers (auth, items, collections, sync, meta, ...)
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── importers/   # CLZ, generic CSV, JSON backup
│   │   ├── hardening.py
│   │   ├── observability.py
│   │   ├── bootstrap.py
│   │   ├── cli.py
│   │   └── main.py
│   ├── alembic/         # Migrations (shipped to /opt/covet/share/covet/alembic in image)
│   └── tests/           # pytest, currently 42 passing
├── web/                 # SvelteKit 2.8 / Svelte 5 runes / adapter-static
│   └── src/{lib,routes,app.html}
├── android/             # AGP 8.7.2, Kotlin 2.0.21, Hilt, Room, Compose
│   └── app/src/main/java/io/github/bradbrownjr/covet/
├── docker/              # Compose examples (standard / postgres / unraid)
├── Dockerfile           # Multi-stage; runs as non-root via PUID/PGID/UMASK
├── .github/workflows/   # ci.yml, release-image.yml, android.yml, release.yml
└── CHANGELOG.md         # User-facing release notes
```

## Tech Stack Versions

- Python 3.12, FastAPI 0.115, SQLAlchemy 2, Alembic, slowapi, structlog, prometheus-client 0.21, uv 0.5.4
- Node 22, SvelteKit 2.8, Svelte 5, adapter-static
- Kotlin 2.0.21, AGP 8.7.2, KSP `2.0.21-1.0.28` (KSP1 worker forced — see gotchas)
- Compose BOM 2024.11, Hilt 2.52, Room 2.6.1, WorkManager 2.10
- Docker buildx multi-arch (linux/amd64, linux/arm64) → GHCR

## CI Gates (must stay green)

- **CI / Server (lint + tests)** — `uv run ruff check .` clean, `uv run pytest -q` 42/42.
- **CI / Web (check + build)** — `npm run check` 0 errors, `npm run build` succeeds.
- **CI / Dependency audit** — `pip-audit` + `npm audit` (soft-fail today; tighten later).
- **CI / Docker build (smoke)** — image builds and `/healthz` answers within timeout.
- **Android / Lint, test, build APK** — `:app:lintDebug`, `:app:testDebugUnitTest`, `:app:assembleDebug`.
- **Release Docker image** — multi-arch push to `ghcr.io/bradbrownjr/covet`.
- **Release** — auto-publish GitHub Release on `v*.*.*` tag.

All workflows opt into Node 24 via `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true`.

---

## Repo-Specific Gotchas

These are bugs we have hit. Re-introducing any of them is a regression.

### `.gitignore` patterns must be root-anchored when they collide with source

Bare `data/` and `config/` rules silently untracked the entire
`android/.../data/` Kotlin source package. **Always use `/data/`, `/config/`
(leading slash) for repo-root runtime dirs.** Never use bare directory names
that could match a source package anywhere in the tree.

### Alembic migrations must be shipped into the Docker image

The runtime image installs Covet as a wheel under `/opt/covet`, so
`alembic/` and `alembic.ini` next to `server/src` are not present at
runtime. The Dockerfile copies them to `/opt/covet/share/covet/` and sets
`COVET_ALEMBIC_DIR`. `bootstrap._find_alembic_dir()` honors this env var,
falls back to the dev repo layout, then to `<sys.prefix>/share/covet/alembic`.
**If you add new migrations, no Dockerfile change is needed**, but if you
ever move `alembic/` you must update both copies.

### Loopback hosts must always be in `allowed_hosts`

The container `HEALTHCHECK` curls `http://127.0.0.1:8000/healthz`. If
`TrustedHostMiddleware` rejects loopback names, the container never goes
healthy and CI's docker smoke test fails with a stream of HTTP 400s.
`config.Settings.model_post_init` injects `localhost`, `127.0.0.1`, `::1`
into `allowed_hosts` automatically; do not remove that block.

### KSP2 AA worker is broken on our toolchain

KSP `2.0.21-1.0.27` and `1.0.28` both crash in the AA worker with
`unexpected jvm signature V` on Hilt processors at Kotlin 2.0.21.
`android/gradle.properties` sets `ksp.useKSP2=false`; the legacy KSP1
worker doesn't have this codepath. Re-enable only after upstream fixes
the AA worker.

### slowapi limit-providers must be static strings, not callables

In our slowapi version, the dynamic `limit-from-request` callable is
invoked with zero args, which breaks any signature taking `request`. Keep
`DEFAULT_GLOBAL_LIMIT` and `DEFAULT_LOGIN_LIMIT` as module-level string
constants in `covet/hardening.py`. Also keep `headers_enabled=False` —
`True` requires a `response: Response` parameter on every route or all
routes 500.

### CSRF middleware must allow missing `Origin` header

Modern browsers always send `Origin` on cross-origin requests, but
TestClient and many CLIs do not send one at all. `OriginCsrfMiddleware`
allows requests with no `Origin` so tests and bearer-auth API clients work.

### Ruff `B008` is globally ignored

FastAPI's `Depends(...)`, `Query(...)`, `Body(...)` idiom requires call
expressions in default arguments. `B008` (function-call-in-default) is in
the global ignore list with an explanation comment. Don't re-enable.

### `okhttp3.JavaNetCookieJar` lives in `okhttp-urlconnection`, not core

It is shipped as a separate artifact. Add `okhttp-urlconnection` (same
version ref as `okhttp`) to `gradle/libs.versions.toml` and reference it
from `app/build.gradle.kts`. Importing it from `okhttp` core gives an
unresolved-reference KSP failure.

### CameraX `ImageProxy.image` opt-in needs BOTH annotation and `lint.xml`

`androidx.camera.core.ExperimentalGetImage` is enforced by lint, not the
compiler. Lint's opt-in propagation through deeply nested lambdas
(`AndroidView` factory → `ProcessCameraProvider` listener →
`ImageAnalysis.setAnalyzer`) is unreliable. Use both:
1. `@OptIn(ExperimentalGetImage::class)` on the enclosing composable.
2. Project-wide opt-in in `android/app/lint.xml` wired via
   `lint { lintConfig = file("lint.xml") }` in `app/build.gradle.kts`.

### Backtick test names cannot contain JVM-illegal method chars

JUnit backtick names compile to JVM method names, which forbid
`.;[]/\<>:`. So `` `round-trips dto -> entity -> dto` `` fails with
`Name contains illegal characters: >`. Use `to`/`then`/`-` instead of
arrows, slashes, dots, etc.

### Local Android build environment (no toolchain in dev container)

CI is the only place this used to build. To validate Android changes
locally before pushing (highly recommended — CI ping-pong is slow):

```bash
apt-get install -y --no-install-recommends openjdk-17-jdk-headless unzip
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64

# Bootstrap gradle-wrapper.jar (gitignored):
curl -fsSL -o /tmp/g.zip https://services.gradle.org/distributions/gradle-8.10.2-bin.zip
unzip -q /tmp/g.zip -d /tmp/g
cd android && /tmp/g/gradle-8.10.2/bin/gradle wrapper --gradle-version 8.10.2 --distribution-type bin

# Android SDK (compileSdk=35):
mkdir -p ~/android-sdk/cmdline-tools && cd ~/android-sdk/cmdline-tools
curl -fsSL -o tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip -q tools.zip && mv cmdline-tools latest
export ANDROID_HOME=$HOME/android-sdk
export PATH=$ANDROID_HOME/cmdline-tools/latest/bin:$PATH
yes | sdkmanager --licenses >/dev/null
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"

cd /home/vscode/code/covet/android
./gradlew :app:lintDebug :app:testDebugUnitTest :app:assembleDebug --no-daemon
```

Lint emits a wall of `WARNING: Missing analysis API method ...
NoWriteActionInAnalyseCallChecker` from AGP 8.7.2's bundled lint vs.
Kotlin 2.0.21 analysis API — known noise, not actionable.

---

## Feature Registry

Compact checklist of shipped user-facing features keyed to their primary
implementation files. **Before any large refactor, verify every row touching
the affected file column is preserved.**

| Feature | Key file(s) | Key identifiers |
|---|---|---|
| Local auth (register, login, password) | `server/src/covet/api/auth.py`, `auth/service.py`, `auth/passwords.py` | `register`, `login`, `Argon2`, `create_user` |
| API tokens (CLI / mobile) | `server/src/covet/api/auth.py` | `POST/GET/DELETE /auth/tokens`, `create_token` |
| Sessions / cookie auth | `server/src/covet/auth/session.py`, `api/auth.py` | `SessionInfoDto`, cookie name from settings |
| Collections CRUD | `server/src/covet/api/collections.py`, `models/collection.py` | `GET/POST/PATCH/DELETE /collections` |
| Items CRUD + filtering | `server/src/covet/api/items.py`, `models/item.py` | `GET/POST/PATCH/DELETE /items`, `?search`, `?type` |
| Tags / item-tags | `server/src/covet/api/tags.py`, `models/tag.py` | `tag`, `item_tag` |
| Contacts + loans | `server/src/covet/api/loans.py`, `models/{contact,loan}.py` | `loan`, `contact` |
| Photos (multipart, sha256 dedupe) | `server/src/covet/api/photos.py`, `models/photo.py` | `POST /photos`, `_photo_path` |
| Sync (CRDT changes + snapshots) | `server/src/covet/api/sync.py`, `sync/automerge.py` | `GET/POST /sync/{collection_id}`, `apply_changes` |
| Importers (CLZ, generic CSV, JSON) | `server/src/covet/importers/{clz,csv_importer,json_backup}.py`, `api/imports.py` | `clz`, `csv`, `json_backup` |
| Backup / restore CLI | `server/src/covet/cli.py`, `importers/json_backup.py` | `covet backup`, `covet restore`, `covet version` |
| Hardening (CSP, rate limit, CSRF) | `server/src/covet/hardening.py` | `SecurityHeadersMiddleware`, `OriginCsrfMiddleware`, `limiter` |
| Observability (access log, metrics) | `server/src/covet/observability.py`, `api/meta.py` | `AccessLogMiddleware`, `/metrics`, `covet_http_requests_total` |
| Health / readiness | `server/src/covet/api/meta.py` | `/healthz`, `/readyz` |
| Web auth flow (login, register, gating) | `web/src/routes/{login,register,+layout.svelte}`, `lib/session.ts` | `me`, `refreshMe`, `logout` |
| Web collections list / detail | `web/src/routes/collections/...` | list view + card grid view, `viewMode` localStorage toggle |
| Web item creator + subtitle fields | `web/src/routes/collections/[id]/+page.svelte` | `newCreator`, `newSubtitle`, Enter-key flow, `attrs.creator` in table |
| Web import wizard | `web/src/routes/import/+page.svelte` | CLZ + CSV + JSON restore |
| Web settings + tokens | `web/src/routes/settings/+page.svelte` | `tokens`, `revoke`, theme toggle |
| Web theme (light/dark/system) | `web/src/lib/theme.ts`, `lib/styles.css`, `app.html` | `initTheme`, `data-theme`, `meta[name=theme-color]`, pre-hydration script |
| Android auth (URL + creds → token) | `android/.../ui/screen/login/LoginScreen.kt`, `data/auth/SessionStore.kt`, `data/repo/AuthRepository.kt` | `SessionStore.baseUrl`, `apiFor` |
| Android collections / items list / add / delete | `android/.../ui/screen/{collections,collection}/...` | `CollectionListViewModel`, `CollectionDetailViewModel` |
| Android pull-to-refresh | `android/.../ui/screen/collection/CollectionDetailScreen.kt` | `PullToRefreshBox`, `pullRefresh()`, `DetailUi.refreshing` |
| Android barcode scanner | `android/.../ui/screen/scan/ScannerScreen.kt` | CameraX + ML Kit `BarcodeScanning` |
| Android Room cache (offline reads) | `android/.../data/local/{CovetDatabase,Mappers}.kt`, `di/DatabaseModule.kt`, `data/repo/Repositories.kt` | `CollectionEntity`, `ItemEntity`, `observe()`, `deleteMissing` |
| Android sync worker (15-min refresh) | `android/.../data/sync/SyncWorker.kt`, `CovetApp.kt` | `SyncWorker.schedule`, `UNIQUE_NAME`, `KEEP` policy |
| Docker image (multi-arch, non-root) | `Dockerfile`, `docker/entrypoint.sh` | `PUID/PGID/UMASK`, `tini`, `gosu`, `COVET_ALEMBIC_DIR` |
| Compose examples | `docker/docker-compose.{standard,postgres,unraid}.yml` | — |
| CI: server lint+tests, web check, audit, docker smoke | `.github/workflows/ci.yml` | jobs `server`, `web`, `audit`, `docker` |
| CI: multi-arch GHCR image | `.github/workflows/release-image.yml` | tag patterns `:X.Y.Z`, `:X.Y`, `:X`, `:edge` |
| CI: Android build + APK artifact | `.github/workflows/android.yml` | `:app:lintDebug`, `:app:testDebugUnitTest`, `:app:assembleDebug` |
| CI: auto-publish Release on tag | `.github/workflows/release.yml` | extracts `## [X.Y.Z]` from `CHANGELOG.md`; `prerelease` for `0.x` |

Update this table whenever a new feature lands or an existing feature moves.

---

## Roadmap

Tracked ideas and planned features that are **not yet built**. Update when
work begins or the idea is abandoned.

### Template editing & cloning
- Server has `ItemTemplate` model + CRUD API (`api/item_templates.py`); items
  have an optional `template_id` foreign key.
- Missing: role-based access check (currently no permission guard on template
  endpoints), a `POST /item-templates/{id}/clone` endpoint, and all UI (web
  template management page, Android template picker).
- The `Membership` model has `viewer/editor/owner` roles — enforce
  `editor`+ for create/edit/clone, any member for read.

### Real-time / live updates
- The app currently polls (15-min Android SyncWorker, manual web refresh).
- No WebSocket or SSE endpoint exists.
- Future: add `GET /collections/{id}/events` SSE stream; push item-added /
  item-updated / item-deleted events; web auto-refreshes item list;
  Android subscribes while the app is in the foreground.

### Collection themes
- Visual skins for the collection detail view, inspired by the physical
  environment of each category.
- **Bookshelf** — wood-grain shelf texture behind box art tiles; books stand
  upright as spine thumbnails.
- **Game room** — dark ambient background with neon-accent category badges;
  cartridge / box art prominently shown.
- **Movie room** — cinematic widescreen header; poster-style grid with rating
  stars.
- Implementation plan (future): add a `theme` field to `Collection` model;
  web collection detail page reads `collection.theme` and applies a
  `data-theme` attribute or CSS class to the root; per-theme CSS modules;
  Android collection detail screen switches background/color tokens.
  Requires photo thumbnails to be exposed in the items list API response.
