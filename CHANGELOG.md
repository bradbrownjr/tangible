# Changelog

All notable changes to **Tangible** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); this project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- **Grocery list: back button and add item** — the Android grocery list screen
  now has a back button in the top bar and a floating action button to add
  ad-hoc items directly from the list.
- **Store aisle sorting** — create grocery stores with ordered aisles, assign
  category slugs to each aisle, then select a store when shopping to have your
  grocery list automatically sorted in aisle order. Manage stores via the
  store icon in the grocery list top bar. Available on Android and via the API
  (`/grocery/stores`).

## [0.17.1] — 2026-05-03

- **Fix grocery list nav link** — the Grocery List link was hidden when
  the list was empty, making it impossible to add the first item. The
  link is now always visible; the count badge only appears when there
  are open entries.

## [0.17.0] — 2026-05-03

- **Rebranded to Tangible** — the app, server, Docker image, Android package,
  and all configuration are now named Tangible. The Docker image is published
  at `ghcr.io/bradbrownjr/tangible`. Environment variables are now prefixed
  `TANGIBLE_*`; the CLI command is `tangible`; the Android package ID is
  `io.github.bradbrownjr.tangible`. Existing deployments must rename env vars
  and re-pull the image under the new name.
- **Shared grocery list** — household members can now add ad-hoc items
  to a shared shopping list per collection, alongside any pantry items
  marked depleted. New `/api/grocery` endpoints (list, create, update,
  delete, mark-purchased). Marking a linked entry purchased restocks the
  pantry item automatically (creates an `ItemLot`, clears `depleted`).
- **Grocery list nav badge** — the Grocery List link is always visible in the
  nav bar. A small badge displays the open count when there is something on
  the list (depleted items + ad-hoc entries).
- **Wider audit-log coverage** — every grocery action plus item create,
  update, delete, flag/unflag and restock now write an `AuditLogEntry`.
  Closes long-standing gaps in the per-collection audit view.

## [0.17.0-rc2] — 2026-05-02

- **Squashed Alembic migrations** — pre-1.0 had 35 incremental migrations
  carried since the first commit; collapsed into a single
  `0001_initial.py` baseline that creates the schema from
  `Base.metadata` and seeds the curated category taxonomy. Cleaner fresh
  installs; no functional change.
- **Fix Android build** — added missing `import retrofit2.http.PUT`
  in `TangibleApi.kt` so the notification preference endpoint compiles
  again. (Regression introduced when notification PUT route was added.)
- Removed unused `size_px` parameter from `_make_qr_png` helper.
- Removed two empty stray top-level files (`category`, `leaf`).

## [0.17.0-rc1] — 2026-05-02

- **i18n & localization** — the web UI now supports multiple languages.
  A language picker in the navigation bar lets users switch between English,
  French, German, Spanish, and Japanese; the preference is saved to
  `localStorage`. The `<html lang>` attribute updates automatically.
  Navigation, auth pages (login, register), and common action labels are fully
  translated. The infrastructure is in place for community contributions via
  the `web/src/lib/locales/` message catalogs.
- **Plugin/adapter system for metadata scrapers** — third-party packages can
  now register custom URL and barcode adapters without modifying Tangible's core.
  Declare adapters in your package's `pyproject.toml` under the
  `tangible.scraper_adapter` or `tangible.barcode_adapter` entry-point groups;
  Tangible auto-discovers and loads them at startup. Admins can verify loaded
  adapters via `GET /metadata/adapters`.
- **Item comment threads** — users can now post, reply to, edit, and delete
  comments on individual items. Comments are threaded (one level of replies),
  shown in a collapsible panel on each item card and table row. Any collection
  member (viewer+) can read and post; authors can edit or delete their own
  comments; editors/owners can delete any comment.
- **MCP server** — Tangible now exposes a [Model Context Protocol](https://modelcontextprotocol.io/)
  endpoint at `/mcp`. AI assistants (Claude, Copilot, ChatGPT plugins, etc.)
  can query your inventory, maintenance history, and stock levels in natural
  language. Configure your AI client with your Tangible server URL and a Bearer
  API token. Tools available: `list_collections`, `search_items`, `get_item`,
  `list_maintenance`, `list_due_alerts`, `list_low_stock`.
- **Enforce 2FA site-wide**: admins can toggle `require_2fa` in the new
  Server Settings panel; unenrolled users are redirected to Settings and
  shown an enrollment prompt automatically on every page load until 2FA
  is set up. `GET /auth/me` now returns `enrollment_required: bool`.
- **Admin Server Settings panel** (Settings page, admin-only): all
  meaningful `TANGIBLE_*` env-var knobs (security, sessions, integrations,
  SMTP) are editable through the UI. DB overrides take precedence over
  env vars without requiring a restart; sensitive values are masked. Each
  field shows its current source (`database` / `environment` / `default`)
  and its corresponding env var name for reference.
- **`GET /config/public`** now includes `require_2fa` so clients can
  adapt before the user even logs in (future use).
- **Migration 0034_app_settings**: new `app_settings` key/value table
  for runtime admin overrides.
### Added

- **Two-factor authentication (TOTP).** Local accounts can now enable 2FA using any TOTP-compatible authenticator app (Google Authenticator, Authy, etc.). Setup generates a QR code and secret displayed in Settings. Activation verifies the first code and issues 8 one-time backup codes. Login detects 2FA and presents a second-step code prompt. Backup codes can be regenerated; 2FA can be disabled with password + current code. API: `POST /auth/totp/setup`, `POST /auth/totp/verify`, `DELETE /auth/totp`, `POST /auth/totp/regenerate-backup-codes`, `POST /auth/totp/confirm-login`.
- **Account data export.** `GET /auth/me/export` downloads a ZIP containing a full JSON backup (compatible with the `tangible restore` CLI and the web import wizard) plus a README.
- **Account self-deletion.** `DELETE /auth/me` permanently deletes the signed-in account and all sole-owned collections. Requires current password; also requires a TOTP code if 2FA is enabled. Web UI provides a confirmation modal in Settings.

- **Tag filter chips with AND/OR mode.** The collection item list now shows clickable tag chips below the filter bar. Select one or more tags to filter items; a toggle switches between **All** (item must have every selected tag) and **Any** (item must have at least one).
- **Drag-to-reorder photos.** In the photo gallery thumbnail strip, photos can be reordered by drag-and-drop while in edit mode. The new order is saved via `PUT /items/{id}/photos/reorder`.
- **Custom sort order on items.** Items have a new `sort_order` integer field. Select "Sort: Custom order" from the sort dropdown to show items in this order. The field is exposed in `PATCH /items/{id}` and a new `PUT /items/reorder` bulk endpoint lets clients rearrange items.
- **Server thumbnail endpoint.** `GET /photos/{id}/thumbnail` returns a 400x400 JPEG thumbnail (lazy-generated on first access using Pillow, cached with `Cache-Control: public, max-age=604800`).
- **Type-ahead autofill for Condition and Creator.** When editing an item inline, the Condition and Creator fields now show a datalist of existing values from the collection so you can stay consistent without typing from scratch. Suggestions are fetched lazily from `GET /collections/{id}/field-suggestions?field=condition|creator`.
- **Admin guide: reverse proxy setup.** The admin guide now includes a full "Reverse proxy setup" section with copy-paste examples for Caddy, Traefik (Docker labels), and nginx, plus an "OIDC provider setup" subsection with Authentik, Keycloak, Authelia, Google, and GitHub configuration notes. A table of contents was also added to the admin guide.

- **Photo gallery with captions.** Each photo now stores an optional caption (migration `0031_photo_caption`). The web collection page shows an inline `PhotoGallery` component with a lightbox viewer, thumbnail strip, keyboard navigation (← → Esc), set-as-primary, delete, and click-to-edit captions.
- **Field-value hyperlink filters.** Category badges, creator, condition, and location tags in the collection grid and table views are now interactive buttons; clicking any value instantly filters the item list to that value.
- **Insurance export web trigger.** The collection subnav now includes an **Export** tab that downloads the insurance-export PDF directly via `GET /api/collections/{id}/reports/insurance-export`.
- **Home Assistant sensor endpoint.** `GET /api/ha/sensors` returns a per-collection JSON sensor payload (item count, low-stock count, overdue alerts, due-soon alerts) ready for HA's `rest` sensor platform. `GET /api/ha/blueprint.yaml` serves a downloadable automation blueprint. Both endpoints accept Bearer token or session auth.
- **NFC tag write/read (Android).** The item detail screen now shows a **Write NFC Tag** button that writes `tangible://item/<id>` to a blank NFC tag using foreground dispatch. Tapping a Tangible NFC tag from anywhere on the device opens the app and navigates directly to the item. The camera scanner also handles `tangible://` QR codes to navigate to an item.
- **Unified physical labeling.** `GET /api/items/{id}/qr.png` returns a PNG QR code encoding `tangible://item/<id>` for printing or display. The existing `POST /items/qr-labels/generate` PDF now embeds real `tangible://item/` QR images instead of text placeholders, making printed labels machine-readable by any Tangible-aware scanner.
- **AI-assisted item creation (`POST /items/ai-prefill`).** Accepts `{ barcode }` and queries the registered barcode adapters (Open Library, MusicBrainz, Open Food Facts, Google Books); returns `{ title, subtitle, category_slug, attrs, source }` so the client can pre-fill the add-item form. Returns an empty response gracefully if no match is found.
- **Three-channel notification preferences.** Each alert kind (maintenance, chores, expiry, etc.) now has three independent channel toggles: **Email**, **Browser**, and **App** — configurable in **Settings → Notifications**. Browser notifications fire once per day when the web app is open and permission is granted. App (Android) notifications respect per-kind on/off switches and each kind's lead time.
- **Quick-action shortcuts for home equipment.** Items in the HVAC/Furnace, Refrigerator, Water Service Filtration, and Generator categories now show a one-tap action button — "Log filter change" or "Ran generator today" — directly on the item card. Each tap auto-creates (or reuses) a dedicated chore and records a completion, keeping maintenance history current without navigating to the Chores tab.

- **Manual / asset bundles.** A new collection-scoped "manual library"
  lets you upload a primary manual plus related assets (diagrams,
  firmware, service sheets, parts lists) once and link the bundle to
  many items. Manage bundles from the new **Bundles** tab on each
  collection: create, upload assets by kind, mark a primary asset,
  link/unlink items. The Android client surfaces linked bundles on
  the item detail screen.
- **Location hierarchy.** Flat `item.location` text is replaced with a
  proper location tree (`home → floor → room → zone → container`, arbitrary
  depth). Manage locations from the new **Locations** tab on each
  collection, then assign items via a dropdown picker in create / edit /
  duplicate / bulk-move flows. Existing free-text locations are migrated
  automatically into per-collection `room` nodes. Android client picks up
  locations through the offline Room cache and exposes the same dropdowns
  in the item detail screen and bulk-move sheet.
- **Phase 11 wave 3 categories (API + web picker).** Sports & Recreation root
  added with Fitness Equipment, Outdoor Gear, and Sports Equipment leaves.
  No new roots for Tools and Pantry (already existed), but scaffold templates
  now available.
- **Phase 11 wave 3 scaffold templates (API + web defaults).** Tools root now
  includes Hand Tool (brand, model, size, purchase/warranty tracking, storage),
  Power Tool (serial, voltage/amperage, battery system, service/blade change),
  and Shop Equipment (service interval). Pantry (spices) root now includes
  Spice (product, category, quantity, unit, best-by, bloom date) and Pantry
  Item (product, category, minimum stock, quantity, unit, best-by, storage
  location). Sports & Recreation root includes Fitness Equipment (type, brand,
  weight, condition, maintenance), Outdoor Gear (type, brand, packed weight,
  capacity, inspection), and Sports Equipment (sport, type, dominant hand,
  restring/reshaft/regrip tracking).
- **Phase 11 vehicle templates completion (API + web defaults).** Remaining
  three vehicle subcategories now have scaffold templates: Boat/PWC (hull ID,
  engine type, winterization, mooring location, registration/insurance),
  Trailer (type, tare/capacity weight, tire replacement, inspection), and
  Bicycle/E-Bike (bike type, frame material, tune-up/chain/brake service,
  e-bike battery capacity and service). All 6 vehicle roots now fully templated.
  Phase 11 dictionary (12 roots, 40+ leaves) and scaffold templates (40+)
  now complete. Remaining Phase 11 features (location hierarchy, manual/asset
  bundles) are deferred and tracked separately.

### Changed

- **"Spices & Pantry" category renamed to "Pantry".** The root category slug
  (`spices`) is unchanged; only the display name is updated.

- **Depleted flag on items.** Any item can be marked as depleted (ran out /
  needs restocking) via the Edit row actions in the collection detail view.
  Depleted items appear dimmed with a strikethrough. Toggle back with "In stock".
- **Duplicate item action (web).** Collection item rows/cards now include a
  **Duplicate** button that creates a copy in the same collection and category,
  carrying over quantity, condition, identifiers, and custom attributes.
- **Item sort controls (web + API).** Collection views now support sorting by
  title, current value, acquisition date, and a custom attribute key. The
  server adds `GET /items` query params `sort_by`, `sort_dir`, and `sort_attr`
  (for custom-field sorting).
- **Barcode scan from still images (web + Android).** You can now pick an
  existing photo from your device and decode barcodes without using the live
  camera preview. Web uses ZXing browser decoding and Android uses ML Kit on
  gallery images, both feeding the existing metadata lookup flow.
- **Parent item value rollup (web + Android + API).** Container/kit items now
  expose a computed `rollup_current_value` equal to the summed value of their
  nested contents, and both clients display that effective value in item lists.
- **Item review flags (web + API).** Editors/owners can now flag items for
  follow-up with an optional note (`POST /items/{id}/flag`) and clear the flag
  (`DELETE /items/{id}/flag`). Flags are also cleared automatically on the next
  normal item edit.
- **Dynamic dropdown template fields (web + API).** Template `select` fields
  can now use `select_source: "dynamic"` to populate choices from values
  already used in that field across the collection, reducing static-option
  maintenance. Added `GET /collections/{collection_id}/template-field-options/{field_key}`.
- **Multi-value template fields (web + API).** Templates now support a
  `multi_value` field type for ordered lists (for example URLs, related ISBNs,
  cast lists). Item validation now accepts both JSON arrays and comma-separated
  strings, coercing values into an ordered list.
- **Relation template fields (web + API).** Templates now support
  a `relation` field type with scope control (`same_collection` or
  `any_collection`) so attrs can point to another item ID with server-side
  validation, and web collection views now render relation mini-cards showing
  linked item labels.
- **Community scraper registry import (web + API).** The Templates page now
  lists curated registry presets from `GET /metadata/registry` and allows
  editors/owners to one-click import them into a collection via
  `POST /metadata/registry/import`. Admins can now override trust status with
  `PATCH /metadata/registry/{entry_id}/trust`.
- **Wanted items (web + API).** Items now support a `wanted` flag so you can
  track not-yet-owned targets in the same collection, filter lists with
  `GET /items?wanted=true/false`, and toggle Wanted/Owned inline from web
  list and grid views. Converting Wanted → Owned now captures acquisition
  date and optional purchase price.
- **Bulk item actions (web + API).** Collection views now support multi-select
  with bulk status updates (wanted/owned, depleted/in-stock), bulk
  archive/restore, bulk delete, bulk tag add/remove, bulk move-to-location,
  and bulk lend-to-contact. The server adds `POST /items/bulk-patch`,
  `POST /items/bulk-archive`, `POST /items/bulk-restore`,
  `POST /items/bulk-delete`, `POST /items/bulk-tags`, and
  `POST /items/bulk-lend`.
- **Android: bulk selection actions parity.** Collection detail now
  supports multi-select in list/grid views with bulk depleted/in-stock,
  bulk wanted/owned, bulk archive/restore, bulk delete, bulk tag
  add/remove, bulk move-to-location, and bulk lend-to-contact using the
  collection-scoped bulk item endpoints.
- **CSV hierarchy round-trip (web + API).** You can now export a collection as
  CSV with stable item/parent references (`GET /imports/csv/export`) and
  re-import it while preserving parent/child relationships using
  `ref:item_ref` + `ref:parent_ref` mapping targets.
- **Archive / sold-disposition workflow (web + API).** Items can now be
  archived instead of deleted via `POST /items/{id}/archive` with optional
  disposition metadata (sold/disposed/donated, date, amount, buyer, note),
  restored via `POST /items/{id}/restore`, and filtered using
  `GET /items?include_archived=true&archived=true`.
- **Expanded item search (web + API).** Collection search now matches
  title/subtitle, notes, and JSON custom fields/identifiers, and web adds
  a `/` keyboard shortcut to focus the search box.
- **Attachment OCR/text indexing in search (API).** Global search
  (`GET /items/search`) now includes indexed attachment text from item
  documents. Text files/PDF text are indexed, and image attachments are
  OCR'd when Tesseract is available.
- **Phase 11 category kickoff (API + web picker).** Added a new
  `home_equipment` category root and starter leaf categories:
  appliance, generator, HVAC/furnace/air-handler, water heater,
  refrigerator, water service filtration, and sump pump.
- **Phase 11 wave 1 defaults (API + web templates).** Added `fuel_chemicals`
  and `vehicles` category roots with starter leaves, and expanded scaffold
  template defaults for `home_equipment`, `fuel_chemicals`, and `vehicles`
  so new collections get practical appliance/fuel/vehicle fields out of the box.
- **Grocery list page.** A new "Grocery List" link in the navigation shows all
  depleted items across every collection you have access to — ideal for shared
  household pantry collections where multiple members need to see what to restock.
  Marking an item "In stock" from this page removes it from the list.
- **`GET /items/grocery-list`** — server endpoint returning all depleted items
  across the authenticated user's accessible collections.
- **`GET /items?depleted=true/false`** — filter items by depleted status.
- **Per-package inventory lots for consumables.** New inventory-lot APIs now track individual purchases
  (quantity, purchased date, use-by, frozen, opened, consumed) so household members can buy a second
  package while an older one is still in stock and rotate FIFO accurately.
- **`POST /items/{item_id}/restock`**, **`GET/POST /items/{item_id}/lots`**,
  **`PATCH /lots/{lot_id}`**, **`POST /lots/{lot_id}/consume`**, and **`POST /lots/{lot_id}/freeze`**
  for lot-level stock lifecycle management.
- **Upcoming due-date alerts API.** New **`GET /alerts`** endpoint returns expiring/use-by/maintenance
  alerts across readable collections for notification surfaces.
- **Web + Android in-app due alerts.** Settings now surfaces upcoming due items (next 14 days) in both
  web and Android to help prevent missed use-by and renewal dates.
- **Admin system scrub control.** New admin-only Settings action calls
  **`POST /admin/system/scrub-inventory`** with typed confirmation to clear inventory-domain data
  during early schema iteration.

### Changed

- **No browser-native confirm dialogs in web flows.** Collection, member/share/invite, template,
  token revoke, and system scrub confirmations now use in-app modal dialogs.

### Fixed

- **Android: "What's new" now loads correctly.** The app was previously showing
  a "malformed JSON" error when tapping "What's new" in the About screen because
  the changelog endpoint returns plain text but Retrofit was trying to parse it
  as JSON. The `ScalarsConverterFactory` is now registered so plain-text
  responses are handled correctly.

### Added

- **Android: delete a collection.** Owners can now delete a collection from the
  collection detail screen. A trash icon appears in the toolbar for owners; tapping
  it shows a confirmation dialog listing how many items will be permanently deleted.
- **Android: copy diagnostics.** A "Copy diagnostics" button in the About screen
  copies app version, Android version, device model, server URL, username, and
  recent log output to the clipboard for easy bug reporting.

## [0.16.1] — 2026-04-30

### Fixed

- **Android: Obtanium still showed two APKs in v0.16.0.** The CI workflow
  now uploads only the signed release APK (`tangible-{version}.apk`) on tagged
  releases, so Obtanium offers a single installable update. Debug APKs are
  still built for every commit but only attached to workflow artifacts, not
  to GitHub Releases.

## [0.16.0] — 2026-04-30

### Added

- **Android: About screen.** New screen (hamburger menu → About) shows the
  app description, installed version, a tappable link to the source
  repository, a "What's new" button that fetches the server changelog, and a
  "Help / User guide" button with an embedded guide.
- **Android: hamburger menu on the collections screen.** The gear icon is
  replaced by a `☰` menu that opens Settings and About, making room for future
  entries without crowding the toolbar.
- **Android: edit collections in the field.** A pencil icon appears in the
  collection detail toolbar for owners and editors. Tapping it opens a dialog
  to rename the collection or update its description; the change is saved via
  `PATCH /collections/{id}`.
- **Android: System / Light / Dark theme selector in Settings.** A three-way
  segmented-button control lets users override the system appearance. The
  preference is stored in DataStore and applied on next launch (and live
  across recomposition in MainActivity).
- **Android: `my_role` on `CollectionDto`.** The DTO now surfaces the
  authenticated user's role in each collection, used to gate the edit button.
- **Docs: Android install guide** (`docs/android-install.md`) — Obtanium
  steps, manual sideloading, Samsung AV scan note, permissions table,
  troubleshooting.
- **Docs: Android user guide** (`docs/android-user-guide.md`) — first-launch
  setup, collections, items, barcode scanning, photos, settings, offline
  behaviour, permissions.

### Fixed

- **Android: Obtanium shows two APKs.** Removed `applicationIdSuffix =
  ".debug"` from the debug build type. Both debug and release builds now share
  the app ID `io.github.bradbrownjr.tangible`, so Android treats them as the
  same application and Obtanium sees only one installable APK per release.

## [0.15.1] — 2026-04-30

### Fixed

- **Android: "Unable to resolve host tangible.invalid" after login.** Retrofit
  was built once at app start; if no server URL had been saved yet it used a
  placeholder host. After login the singleton was never rebuilt so every API
  call until the next app restart would fail. A new `BaseUrlInterceptor`
  rewrites the host on every request from the saved URL, so API calls work
  immediately after login without restarting the app.
- **Android: category pre-selection in the add-item dialog.** When a category
  filter chip is active, opening the add dialog now pre-selects that category
  (root + leaf) so new items land in the right place.
- **Android: Obtanium update conflict.** CI now signs every APK (debug and
  release) with the same keystore, giving Android a consistent signature to
  verify against across updates.
- **Android: collection delete wiped entire local cache.** `deleteById` now
  removes only the targeted collection from the Room cache instead of clearing
  everything.

### Added

- **Android: item detail & edit screen.** Tap any item to see all its fields
  (subtitle, notes, condition, quantity, purchase price, current value,
  currency, location). Tap the pencil icon to edit inline; Save sends a PATCH
  to the server and updates the local cache.
- **Android: search bar on collection detail screen.** Type and press Search
  to filter items server-side; tap ✕ to return to the full list.
- **Android: category filter chips on collection detail screen.** A horizontal
  row of chips appears when a collection has items in 2+ categories. Tapping
  a chip filters the list and pre-selects that category in the add-item dialog.

## [0.15.0] — 2026-04-30

### Added

- **Multi-source barcode lookup (Android + server).** Scanning a barcode
  now queries Open Library (books), MusicBrainz (music), Open Food Facts
  (grocery/household), and Google Books (optional API key) in parallel.
  When multiple matches are found a picker card list lets you choose the
  right one; a single match auto-fills; no match opens a blank form.
  A "Looking up barcode…" overlay shows while the search is in progress.
- **Pull-to-refresh on the collections list (Android).** Swipe down on
  the collections list to reload — was already wired on the item list but
  missing from the top-level screen.
- **Retry button on error states (Android).** Both the collections list
  and the item list now show a Retry button when a network error occurs,
  instead of just displaying the error text.
- **Test Connection button in Settings (Android).** Tap to verify the
  server URL is reachable; shows inline pass/fail feedback without
  leaving the screen.
- **`TANGIBLE_GOOGLE_BOOKS_API_KEY` config option.** Optional environment
  variable to use an authenticated Google Books quota (1000 req/day free
  tier) for barcode lookups. Falls back to unauthenticated if unset.

### Fixed

- **Android add-item dialog no longer pre-selects a category** for
  collections that have no default category set. Previously "music > vinyl"
  (the first category alphabetically) was silently pre-selected, causing
  items to be filed under the wrong category. The dropdowns now show
  "Select…" with an error outline until the user makes an explicit choice,
  and the Add button stays disabled until both a category and title are set.

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
  APK to each release as `tangible-<version>-debug.apk`.

### Fixed

- **Same-origin POSTs no longer return 403.** The CSRF middleware
  treated `*` in `TANGIBLE_ALLOWED_HOSTS` as a literal hostname and
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
- **Default `TANGIBLE_ALLOWED_HOSTS` for the Unraid sample is now `*`.**
  The previous example assumed the user already had a public hostname
  + reverse proxy and would lock out plain LAN access at
  `http://<unraid-ip>:8000/`. The proxy hostname is now opt-in via
  `TANGIBLE_PUBLIC_URL` / `TANGIBLE_BEHIND_PROXY` overrides.

### Changed

- **First registered user is auto-promoted to admin.** When the database
  contains zero users, `POST /auth/register` always succeeds and the new
  account is created with `is_admin=true`, regardless of the
  `TANGIBLE_REGISTRATION_ENABLED` setting. After that initial signup the
  normal registration gate applies. This removes the need to set
  `TANGIBLE_ADMIN_USERNAME` / `TANGIBLE_ADMIN_PASSWORD` for casual deployments
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
  providers via `oidc_providers:` in `tangible.yaml`. New endpoints
  `/auth/oidc/{provider}/login` and `/auth/oidc/{provider}/callback`
  perform the full authorization-code flow via Authlib, then mint a
  Tangible session cookie. First login creates a user (or links to an
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
  drivers selectable via `TANGIBLE_DATABASE_URL`.
- Auth: local username + Argon2 password, session cookies, opaque API
  tokens for non-browser clients. OIDC scaffolding present (provider config
  in env, full UI flow lands in 1.0).
- Collections, items, tags, contacts, loans, photos (multipart, dedupe by
  sha256, on-disk under `DATA_DIR/photos/<sha[0:2]>/<sha>`).
- Importers: CLZ Movies/Music/Games/Books/Comics, generic CSV with column
  mapping, Tangible JSON backup. Exports: per-type CSV + unified, JSON backup.
- CRDT sync skeleton (Automerge document per item, append-only change log,
  snapshot compaction). Cross-language interop with `automerge-kt` and JS
  is verified by the test suite. Mobile push lands in 1.0.
- Hardening: `SecurityHeadersMiddleware` (CSP, X-Frame-Options, COOP/CORP,
  HSTS), slowapi rate limits (120/min global, 5/min on `/auth/login` and
  `/auth/register`), `OriginCsrfMiddleware` for cookie-auth POSTs.
- Observability: structlog access log, Prometheus `/metrics` with route
  templates, `/healthz` (liveness) + `/readyz` (DB ping).
- CLI: `tangible backup <user> <out>`, `tangible restore <user> <in>`,
  `tangible version`, `tangible bootstrap-admin`.

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
  (`ghcr.io/bradbrownjr/tangible`) with non-root runtime, configurable
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
