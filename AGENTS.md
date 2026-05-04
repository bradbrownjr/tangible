# Agent Guide for Tangible

This file is the persistent shared memory for any AI assistant working on
Tangible (GitHub Copilot, Claude, etc.). It captures the rules of engagement,
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
- No emoji in code, comments, commit messages, or generated docs unless
  explicitly requested.
- No em-dashes in source code or generated text — use commas, periods,
  or parentheses.

## Engineering Principles

- **DRY** — Extract shared logic; don't duplicate.
- **SOLID** — Single-responsibility, open/closed, dependency-inversion.
- **KISS** — Clarity over cleverness. Simple, explicit, maintainable.
- Match the patterns already established in the codebase.
- Progressive cleanup — remove dead imports / commented blocks as you go.

## Implementation Discipline

- Only make changes that are directly requested or clearly necessary.
- Don't add features, refactor code, or make "improvements" beyond scope.
- Don't add docstrings, comments, or type annotations to code you didn't
  change.
- Don't add error handling for scenarios that can't happen. Validate at
  system boundaries only.
- Don't create helpers or abstractions for one-time operations.

## Subagent Usage

- Prefer subagents (e.g., `Explore`) for read-only multi-step research
  to avoid cluttering the main conversation. Safe to call in parallel.
- Specify thoroughness explicitly (quick / medium / thorough).
- Subagents are stateless — give them complete context in the prompt
  and tell them exactly what to return.

## Validate Locally Before Pushing

- CI ping-pong (push → wait → fix → push) is the slowest feedback loop.
- If a toolchain is missing locally (JDK, Android SDK, etc.), install it
  once rather than firefighting per CI run. See the local Android build
  block under "Repo-Specific Gotchas" for the one-time setup.
- Symptom of falling into the trap: "fix one error, push, new error,
  fix, push" cycle. Stop and audit holistically.

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
- **After every targeted edit, read the surrounding ~10 lines** above and
  below the change. Verify that structural markers (braces, indentation
  blocks, closing tags, closing parentheses) are still balanced and that
  no dangling fragment was left behind. This applies regardless of language.
  A structurally broken file will compile-error at a point far from the
  edit, making root-cause diagnosis slow.
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
   - `server/src/tangible/__init__.py` (`__version__`)
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
tangible/
├── server/              # FastAPI + SQLAlchemy + Alembic (Python 3.12, uv, ruff, pytest)
│   ├── src/tangible/
│   │   ├── api/         # Routers (auth, items, collections, sync, meta, ...)
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic schemas
│   │   ├── importers/   # CLZ, generic CSV, JSON backup
│   │   ├── hardening.py
│   │   ├── observability.py
│   │   ├── bootstrap.py
│   │   ├── cli.py
│   │   └── main.py
│   ├── alembic/         # Migrations (shipped to /opt/tangible/share/tangible/alembic in image)
│   └── tests/           # pytest, currently 42 passing
├── web/                 # SvelteKit 2.8 / Svelte 5 runes / adapter-static
│   └── src/{lib,routes,app.html}
├── android/             # AGP 8.7.2, Kotlin 2.0.21, Hilt, Room, Compose
│   └── app/src/main/java/io/github/bradbrownjr/tangible/
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
- **Release Docker image** — multi-arch push to `ghcr.io/bradbrownjr/tangible`.
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

The runtime image installs Tangible as a wheel under `/opt/tangible`, so
`alembic/` and `alembic.ini` next to `server/src` are not present at
runtime. The Dockerfile copies them to `/opt/tangible/share/tangible/` and sets
`TANGIBLE_ALEMBIC_DIR`. `bootstrap._find_alembic_dir()` honors this env var,
falls back to the dev repo layout, then to `<sys.prefix>/share/tangible/alembic`.
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
constants in `tangible/hardening.py`. Also keep `headers_enabled=False` —
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

### New Kotlin types used in a file must be explicitly imported

Kotlin does not auto-import. Any new DTO or class introduced into a
file (even from the same package's sibling module) requires an explicit
`import` statement. Always verify imports compile after adding a new
type reference — the compiler error is `Unresolved reference 'XyzDto'`
cascading into multiple spurious secondary errors. Caught too late in CI.

Example: adding `availableCategories: List<CategoryDto>` to `ShoppingListUi`
without `import io.github.bradbrownjr.tangible.data.remote.CategoryDto`
caused 8 compile errors across the file.

### Android `strings.xml` — new strings must be added to ALL locale files

Android lint (`MissingTranslation`) is **an error, not a warning** and
will fail the build. When adding any `<string name="...">` to
`values/strings.xml`, immediately add translations for the same key in:
`values-de/`, `values-es/`, `values-fr/`, `values-it/`, `values-ja/`,
`values-zh-rCN/`.

If a good translation is not available, use `tools:ignore="MissingTranslation"`
on the element in the base file rather than shipping untranslated text or
skipping the locales.

### Removing a wrapper composable — delete BOTH its opening AND closing brace

When removing a wrapper composable (e.g. `Box`, `Column`, `Card`) that
wraps other composables, you must delete both the opening call **and** its
matching closing `}`. Deleting only the opening leaves a stray `}` that
unbalances the brace tree. Kotlin's parser then treats everything after the
imbalance point as top-level declarations, producing a cascade of
`Expecting a top level declaration` / `Function declaration must have a name`
errors from KSP, not from `kotlinc` directly.

To catch this before pushing: after any composable-wrapper removal, count
that the nesting depth at the end of the function is zero (i.e. the final
`}` of the outermost composable closes at the correct indentation level).

### Local Android build environment (no toolchain in dev container)

**The Android toolchain IS installed in this dev container** — JDK 17 at
`/usr/lib/jvm/java-17-openjdk-amd64`, SDK at `~/android-sdk`. **Always
run the local Android build before pushing any change to `android/`**, do
not rely on CI to catch syntax errors. v0.17.13 through v0.17.17 all
shipped with a broken `ShoppingListScreen.kt` because each release
trusted CI to run later, and CI failures snowballed into 4 patch
releases. One local build run takes ~5 minutes; four CI failures take
hours.

The minimum local check before any tag:

```bash
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
       ANDROID_HOME=$HOME/android-sdk \
       PATH=$HOME/android-sdk/cmdline-tools/latest/bin:$PATH
cd android && ./gradlew :app:lintDebug :app:testDebugUnitTest :app:assembleDebug --no-daemon
```

If the toolchain is ever absent, install it once with:

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

cd /home/vscode/code/tangible/android
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
| Local auth (register, login, password) | `server/src/tangible/api/auth.py`, `auth/service.py`, `auth/passwords.py` | `register`, `login`, `Argon2`, `create_user` |
| API tokens (CLI / mobile) | `server/src/tangible/api/auth.py` | `POST/GET/DELETE /auth/tokens`, `create_token` |
| Sessions / cookie auth | `server/src/tangible/auth/session.py`, `api/auth.py` | `SessionInfoDto`, cookie name from settings |
| TOTP 2FA | `server/src/tangible/api/auth.py`, `models/user.py`, `alembic/versions/0033_totp.py`, `web/src/routes/settings/+page.svelte`, `web/src/routes/login/+page.svelte` | `totp_enabled`, `totp_secret`, `totp_backup_codes`, `POST /auth/totp/setup`, `POST /auth/totp/verify`, `DELETE /auth/totp`, `POST /auth/totp/confirm-login` |
| Account export + deletion | `server/src/tangible/api/auth.py` | `GET /auth/me/export`, `DELETE /auth/me`, `AccountDeleteRequest` |
| Collections CRUD | `server/src/tangible/api/collections.py`, `models/collection.py` | `GET/POST/PATCH/DELETE /collections` |
| Items CRUD + filtering | `server/src/tangible/api/items.py`, `models/item.py` | `GET/POST/PATCH/DELETE /items`, `?search`, `?type` |
| Location hierarchy (tree, item.location_id) | `server/src/tangible/api/locations.py`, `models/location.py`, `web/src/routes/collections/[id]/locations/+page.svelte`, android `data/local/TangibleDatabase.kt` (`LocationEntity`/`LocationDao`) | `GET/POST/PATCH/DELETE /collections/{id}/locations`, `home\|floor\|room\|zone\|container`, `Item.location_id` |
| Tags / item-tags | `server/src/tangible/api/tags.py`, `models/tag.py` | `tag`, `item_tag` |
| Contacts + loans | `server/src/tangible/api/loans.py`, `models/{contact,loan}.py` | `loan`, `contact` |
| Photos (multipart, sha256 dedupe) | `server/src/tangible/api/photos.py`, `models/photo.py` | `POST /photos`, `_photo_path` |
| Photo thumbnails (lazy 400x400 JPEG) | `server/src/tangible/api/photos.py` | `GET /photos/{id}/thumbnail`, `_ensure_thumbnail`, `_thumbnail_path` |
| Photo drag-to-reorder | `server/src/tangible/api/photos.py`, `web/src/lib/PhotoGallery.svelte` | `PUT /items/{id}/photos/reorder`, `PhotoReorderEntry`, `ondragstart/ondragover/ondragend` |
| Item custom sort order | `server/src/tangible/models/item.py`, `api/items.py`, `schemas/item.py`, `alembic/versions/0032_item_sort_order.py` | `sort_order`, `PUT /items/reorder`, `ItemReorderEntry`, `sort_by=sort_order` |
| Tag filter chips (AND/OR) | `server/src/tangible/api/items.py`, `web/src/routes/collections/[id]/+page.svelte` | `tag_ids`, `tag_mode`, `toggleTagFilter`, `.tag-chip`, `.tag-mode-toggle` |
| Field-suggestions type-ahead | `server/src/tangible/api/collections.py`, `web/src/routes/collections/[id]/+page.svelte` | `GET /{id}/field-suggestions`, `_ALLOWED_SUGGESTION_FIELDS`, `conditionSuggestions`, `creatorSuggestions` |
| Manual / asset bundles | `server/src/tangible/api/manual_bundles.py`, `models/manual_bundle.py`, `web/src/routes/collections/[id]/bundles/+page.svelte`, android `data/repo/Repositories.kt` (`BundleRepository`) | `GET/POST/PATCH/DELETE /collections/{id}/bundles`, `POST /bundles/{id}/assets`, `POST /bundles/{id}/items/{item_id}` |
| Sync (CRDT changes + snapshots) | `server/src/tangible/api/sync.py`, `sync/automerge.py` | `GET/POST /sync/{collection_id}`, `apply_changes` |
| Importers (CLZ, generic CSV, JSON) | `server/src/tangible/importers/{clz,csv_importer,json_backup}.py`, `api/imports.py` | `clz`, `csv`, `json_backup` |
| Backup / restore CLI | `server/src/tangible/cli.py`, `importers/json_backup.py` | `tangible backup`, `tangible restore`, `tangible version` |
| Hardening (CSP, rate limit, CSRF) | `server/src/tangible/hardening.py` | `SecurityHeadersMiddleware`, `OriginCsrfMiddleware`, `limiter` |
| Observability (access log, metrics) | `server/src/tangible/observability.py`, `api/meta.py` | `AccessLogMiddleware`, `/metrics`, `tangible_http_requests_total` |
| Health / readiness | `server/src/tangible/api/meta.py` | `/healthz`, `/readyz` |
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
| Android Room cache (offline reads) | `android/.../data/local/{TangibleDatabase,Mappers}.kt`, `di/DatabaseModule.kt`, `data/repo/Repositories.kt` | `CollectionEntity`, `ItemEntity`, `observe()`, `deleteMissing` |
| Android sync worker (15-min refresh) | `android/.../data/sync/SyncWorker.kt`, `TangibleApp.kt` | `SyncWorker.schedule`, `UNIQUE_NAME`, `KEEP` policy |
| Docker image (multi-arch, non-root) | `Dockerfile`, `docker/entrypoint.sh` | `PUID/PGID/UMASK`, `tini`, `gosu`, `TANGIBLE_ALEMBIC_DIR` |
| Compose examples | `docker/docker-compose.{standard,postgres,unraid}.yml` | — |
| CI: server lint+tests, web check, audit, docker smoke | `.github/workflows/ci.yml` | jobs `server`, `web`, `audit`, `docker` |
| CI: multi-arch GHCR image | `.github/workflows/release-image.yml` | tag patterns `:X.Y.Z`, `:X.Y`, `:X`, `:edge` |
| CI: Android build + APK artifact | `.github/workflows/android.yml` | `:app:lintDebug`, `:app:testDebugUnitTest`, `:app:assembleDebug` |
| CI: auto-publish Release on tag | `.github/workflows/release.yml` | extracts `## [X.Y.Z]` from `CHANGELOG.md`; `prerelease` for `0.x` |
| MCP server | `server/src/tangible/api/mcp_server.py` | `FastMCP`, `mcp_app()`, mounted at `/mcp`, tools: `list_collections`, `search_items`, `get_item`, `list_maintenance`, `list_due_alerts`, `list_low_stock` |
| Item comment threads | `server/src/tangible/api/comments.py`, `models/item_comment.py`, `alembic/versions/0035_item_comments.py`, `web/src/lib/ItemComments.svelte` | `GET/POST /items/{id}/comments`, `GET /items/{id}/comments/{parent_id}/replies`, `PATCH/DELETE /comments/{id}`, `ItemComment`, `CommentAuthor`, `ItemComments` component |
| Scraper plugin/adapter system | `server/src/tangible/services/metadata.py`, `api/metadata.py` | `register_adapter`, `register_barcode_adapter`, `discover_plugins`, `list_adapters`, `GET /metadata/adapters`, entry-point groups `tangible.scraper_adapter` / `tangible.barcode_adapter` |
| Shared shopping list (ad-hoc + depleted-item feed) | `server/src/tangible/api/shopping.py`, `models/shopping.py`, `schemas/shopping.py`, `web/src/routes/grocery-list/+page.svelte`, `web/src/routes/+layout.svelte`, `web/src/lib/ShoppingStoreManager.svelte` | `ShoppingItem`, `GET/POST/PATCH/DELETE /lists`, `POST /lists/{id}/purchase`, `GET /lists/count`, `ShoppingFeedEntry`, conditional nav badge; `/grocery/*` 307-redirects to `/lists/*` for older clients |

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
