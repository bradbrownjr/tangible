# Changelog

All notable changes to **Tangible** are documented here.

## [Unreleased]

## [0.25.72] — 2026-05-19

### Added

- **Standalone chores (no collection required):** Chores like "Take out trash" can now be created without belonging to any collection. A `— No collection (standalone)` option appears first in the collection picker on both the web Tasks page and the Android global Tasks screen. Standalone chores are owned by the creating user and surface in the personal alerts feed.
- **New API endpoints:** `GET /chores` (list user's standalone chores) and `POST /chores` (create standalone chore) added to the backend.

### Changed

- `chores.collection_id` is now nullable in the database (migration `0003_standalone_chores`). Existing chores are unaffected.
- Web chore form no longer auto-selects the first collection; Save is enabled as soon as a chore name is entered.
- Android `NewChoreDialog` collection picker always visible, with "— No collection (standalone)" as the default choice. "Manage Chores" shortcut on alert cards is hidden for standalone chore alerts.

## [0.25.71] — 2026-05-19

### Fixed

- **Category picker card height uniformity (Lists & Collections):** Cards in the "New list" and "New collection" category pickers varied in height depending on description length, producing an uneven grid. All cards are now a fixed uniform height (`9rem`) with `overflow: hidden`, and the grid no longer uses `align-items: start`.

## [0.25.70] — 2026-05-19

### Security

- **LoginRequest unbounded fields (DoS):** `POST /auth/login` accepted arbitrarily long `username` and `password` strings. Because Argon2 is intentionally CPU/memory-intensive, a crafted request with a multi-megabyte password string could amplify CPU burn even under the 5 req/min rate limit. Added `max_length=64` to `username` and `max_length=1024` to `password` in `LoginRequest`, matching the limits already in place on the registration endpoint.
- **Content-Disposition header injection:** Collection names and usernames were interpolated directly into `Content-Disposition` response headers without sanitization (e.g. `attachment; filename=bom-{collection.name}.txt`). A name containing `\r\n` could inject additional HTTP response headers. Added `_safe_filename()` helper (strips `\r`, `\n`, `"`, `\\`) in `api/items.py`, `api/collections.py`, and `api/auth.py`, applied to all four affected download endpoints. Filenames are now also consistently double-quoted per RFC 6266.
- **Unbounded `notes` fields (storage DoS):** `notes` fields on `Item`, `MaintenanceTask`, `Chore`, `ChoreCompletePayload`, `MaintenanceCompletePayload`, `QuickChorePayload`, `StandaloneTask`, `Contact`, `Loan`, and `ItemLot` input schemas had no `max_length` constraint. Added `Field(default=None, max_length=65535)` to all affected input schemas; read schemas are unaffected.

## [0.25.69] — 2026-05-19

### Fixed

- **Chores tab stuck progress indicator (Android):** If a `CancellationException` was thrown inside the `refresh()` coroutine (e.g. from structured-concurrency cancellation), the rethrow caused the coroutine to exit before reaching the `_state.value = ... loading = false` assignment, leaving `loading` permanently `true`. Moved the state update into a `finally` block so `loading` is guaranteed to be cleared to `false` regardless of whether the coroutine completes normally, times out, encounters a network error, or is cancelled.

## [0.25.68] — 2026-05-19

### Fixed

- **Home search box header background (Android):** v0.25.67 placed `padding` on the `Surface` modifier, which shrank the Surface's drawn background and exposed the Scaffold's dark background color in the gaps. Moved `padding(horizontal=8dp, vertical=4dp)` to the `TextField` modifier instead — the Surface keeps `height=48dp` and fills the full header bar, while the padding reduces the constraints passed to the TextField (40dp), keeping the outline border inset within the header-colored background.

## [0.25.67] — 2026-05-19

### Changed

- **Home search box outer padding (Android):** Added `padding(horizontal=8dp, vertical=4dp)` to the search `Surface` so the outline border has breathing room on all sides (8dp from screen edges, 4dp gap above and below). Reduced `Surface.height` from 48dp to 40dp and set `contentPadding(top=12dp, bottom=12dp)` so the text (`bodySmall` line-height 16dp: 12+16+12=40dp) fills the field exactly. Total topBar height remains 112dp (64dp TopAppBar + 48dp row).

## [0.25.66] — 2026-05-19

### Fixed

- **Home header height (Android):** The `OutlinedTextField` was still rendering at Material3's hard `minHeight = 56dp` despite the `contentPadding` override introduced in v0.25.65. Added `.height(48.dp)` to the wrapping `Surface`, which passes an exact height constraint that bypasses `defaultMinSize` internally. Removed the now-redundant `contentPadding` override. Home topBar is now 64dp (TopAppBar) + 48dp (search Surface) = 112dp, matching every other section's 112dp header. Fixes visible header-height mismatch during HorizontalPager swipe transitions.

## [0.25.65] — 2026-05-19

### Changed

- **Home search box height (Android):** Migrated `OutlinedTextField` from the `value/onValueChange` overload to the `TextFieldState` overload, which exposes `contentPadding`. Setting `top = 14dp / bottom = 14dp` reduces the field height from ~56dp to ~48dp, matching the tab-row height used by every other section header. Text changes are propagated to the ViewModel via `snapshotFlow`; the clear button edits `TextFieldState` directly.

## [0.25.64] — 2026-05-19

### Changed

- **Home header padding (Android):** Removed outer vertical padding on the search box `Surface`, narrowing the header so the search box sits flush.
- **Alerts chip row padding (Android):** Removed top/bottom padding on the date-filter chip row; the row now matches the ~48dp tab-row height of other section headers.
- **Category picker card alignment (Web):** Preset grids (`.presets`) now use `align-items: start` so cards are anchored to the top edge regardless of description length. Previously `align-items: stretch` caused shorter cards to gain empty whitespace below their content.
- **Status / nav bar icon color (Android):** Added a `SideEffect` in `MainActivity` that calls `WindowCompat.getInsetsController` to sync `isAppearanceLightStatusBars` and `isAppearanceLightNavigationBars` with the active theme. Dark themes get white icons; light themes get dark icons; switches apply instantly on theme change.

### Docs

- **DESIGN.md:** Added "Preset/category picker grid" rule documenting `align-items: start` + `justify-content: flex-start` and why `align-items: stretch` is forbidden.

## [0.25.63] — 2026-05-19

### Changed

- **Header / tab-row uniformity (Android):** Multiple screens brought in line so every section header row is the same height as the `TabRow` (~48dp):
  - Home: search box shrunk; redundant bell icon removed from `TopAppBar`.
  - Collections: `+` button moved into the `ScrollableTabRow`; QR scan, image add, and add-item actions moved to per-tab toolbar rows.
  - Lists: `+` button placed directly inside `ScrollableTabRow`, after the last tab, using the correct `Surface` background.
  - Alerts: date-filter chip row vertical padding reduced.
  - Tasks: `Refresh` and `Add` removed from `TopAppBar`; pull-to-refresh and card-level affordances handle those actions.

## [0.25.62] — 2026-05-19

### Fixed

- **Collections / Lists `+` tab not updating content (Web):** The wizard open/close state was held in local `$state(pickerOpen)` and checked only in `onMount`. SvelteKit does not remount the page on query-param changes, so clicking the `+` tab changed the URL but left the wizard closed. Fixed by deriving `pickerOpen` from `page.url.searchParams`; a `$effect` resets `chosen`, `formName`, `formDescription`, and `error` whenever the picker closes. `cancel()` and `openPicker()` now navigate rather than toggling local state.

## [0.25.61] — 2026-05-19

### Changed

- **Home search field placement (Android):** Moved the search `OutlinedTextField` into `topBar` so it no longer creates a jagged layout during section swipes.
- **Stores spacer row (Android):** Added 48dp spacer row in `topBar` to match the Lists tab-strip height.
- **Alerts day-filter chips (Android):** Moved filter chips into a `topBar` `Surface` row, matching the Collections/Lists pattern.
- **Home Jump-To grid (Android):** Capped the tile grid at 4 columns in landscape (≥768px).
- **Collections `+` tab (Web):** Added a `+` tab button in the tab strip.
- **Lists `+` tab (Web):** Repositioned `+` button directly after the last tab (removed `margin-left: auto`).
- **Lists / All (Web):** Restored the dashed "New list" card in the presets grid.
- **Collections label (Web):** Removed redundant `+ ` prefix from all 7 locale files.

### Fixed

- Added `cd_add_list_type` string to all 6 non-English Android locale files.

## [0.25.60] — 2026-05-19

### Fixed

- **Missing `cd_add_list_type` string (Android):** Added the missing content description string that caused a lint failure in v0.25.59.

## [0.25.59] — 2026-05-19

### Changed

- **Header flow polish (Android):** `AlertsScreen`, `ShoppingListScreen`, and `HomeTabScreen` refactored to keep header rows inside `topBar` (eliminates layout shift during swipe navigation).
- **Per-type store selection (Android):** `ShoppingStoreScreen` now filters stores by list type; users see only the stores relevant to the current list.
- **Lists `[type]` page rewrite (Web):** `lists/[type]/+page.svelte` now fetches `UserListType` dynamically; removed all hardcoded type slugs. Added `lists/+layout.svelte` for shared list context.
- **Home tile quick-links (Web):** Added list-type shortcuts to the home page.

## [0.25.58] — 2026-05-18

### Fixed

- **Nav tab deep-links not switching active tab (Web):** SPA navigation to the same route with a different query param was not re-activating the correct tab. Fixed by keying the active-tab effect on `page.url` rather than component mount.

## [0.25.57] — 2026-05-18

### Fixed

- **Orphaned CSS on Tasks page (Web):** Removed dead `.group`, `.group-title`, and `.group-count` CSS rules that were left after the Tasks page was restructured.

## [0.25.56] — 2026-05-18

### Fixed

- **Infinite `$effect` reactive loop on Tasks / Chores / Scoreboard tabs (Web):** A `$effect` that wrote to a reactive variable it also read was causing an infinite update cycle. Refactored to use a derived value instead.

## [0.25.55] — 2026-05-18

### Changed

- **API rate limit (Server):** Wired the `rate_limit_api` config setting to the rate limiter middleware. Raised the default from 60 to 300 requests per minute.

## [0.25.54] — 2026-05-18

### Fixed

- **`chosen.name` crash on Lists page (Web):** Accessing `.name` before checking if `chosen` is defined caused a runtime crash when the wizard was dismissed quickly.
- **Import page `$app/stores` API (Web):** Updated import to use the current SvelteKit API (`$app/state` instead of deprecated `$app/stores`).
- **`0002` migration on fresh installs (Server):** The performance-index migration failed on databases that had not yet run `0001`. Added a dependency guard so migrations apply in the correct order.

## [0.25.53] — 2026-05-18

### Added

- **Offline mutation queue (Android):** `MutationDrainerWorker` enqueues item creates/updates/deletes when the device is offline and drains them when connectivity is restored.
- **Chores screen (Android):** Dedicated `ChoresScreen` with collection-scoped chore list, completion flow, and inline create.
- **Performance indexes (Server):** Migration `0002_add_perf_indexes` adds covering indexes on `items.collection_id`, `items.archived`, `maintenance_tasks.item_id`, and `maintenance_tasks.next_due` to speed up list and alert queries on large datasets.

### Changed

- **Maintenance API (Server):** `/maintenance/alerts` now supports `kind` filter and returns `collection_name` on each alert for cross-collection views.
- **Settings screen (Android):** Moved chore management and alert counts out of Settings; they now live in the dedicated Chores and Alerts tabs.

## [0.25.52] — 2026-05-18

### Added

- **11-palette theming (Android):** `Theme.kt` now defines all 11 palettes (Blackboard, Blues, Cloud, Espresso, Gazette, Granite, One Dark, Paper, Passion, Tangible, Tron) with full light + dark Material3 color schemes mapped from the web design tokens. Material You dynamic color is replaced; palette selection is authoritative.
- **Palette picker in Settings (Android):** `Settings → Appearance` shows a 3-column swatch grid (background + accent preview, checkmark on selection). Palette persists via `SessionStore`.

### Changed

- **Default palette (Android):** Changed from Material You dynamic to Granite (charcoal/teal), matching the web default.

## [0.25.51] — 2026-05-18

### Changed

- **Settings screen tabbed layout (Android):** Settings is now a 3-tab screen (Appearance / Notifications / Account) using `HorizontalPager + TabRow`.
  - Appearance: theme toggle + language picker.
  - Notifications: per-kind push toggle switches.
  - Account: server URL, username, test connection, sign out, About.
- Removed the inline Alerts / Due Soon section from Settings (the dedicated Alerts nav section handles this).

## [0.25.50] — 2026-05-18

### Fixed

- **Collections `TopAppBar` title (Android):** Shows "Collections" on the All tab instead of "All".
- **"My Stores" renamed to "Stores" (Android):** Corrected the `R.string.stores` resource to match the nav label.

## [0.25.49] — 2026-05-18

### Changed

- **Swipe navigation between tabs and sections (Android):** `HomeScreen` `HorizontalPager` now has `userScrollEnabled = true` so content-area swipes navigate sections on screens without inner pagers (Home, Stores, Alerts, Settings, About). `MaintenanceScreen` replaced `ScrollableTabRow + index` with `HorizontalPager` so Chores / My Tasks / Scoreboard tabs respond to swipe gestures.

## [0.25.48] — 2026-05-18

### Changed

- **New store card in store sidebar (Android):** Replaced the always-open create-store form with a dashed "New store" card. Clicking the card opens the inline form; a cancel button dismisses it. Matches the `OutlinedCard` dashed pattern used by Collections, Lists, and Tasks.

## [0.25.47] — 2026-05-18

### Changed

- **Inline New cards for web index pages (Web):** Collections, Lists, Tasks/Chores, and Tasks/My Tasks pages all now use the dashed "New X" card as the last item in the content grid, with no separate top-of-page button. This brings all index pages into conformance with the `DESIGN.md` page anatomy.

### Docs

- **DESIGN.md:** Updated Primary action spec to the inline New card pattern; documented index vs. detail UX levels; added CSS reference snippet.

## [0.25.46] — 2026-05-17

### Changed

- **Inline New cards for Chores and Tasks tabs (Android):** Replaced empty-state text on Chores and My Tasks tabs with always-visible `NewChoreCard` / `NewTaskCard` (`OutlinedCard`, full-width, `+` icon). Cards trigger the existing create dialogs.

## [0.25.45] — 2026-05-17

### Changed

- **Inline "New" cards for Lists and Stores (Android):** Lists All tab replaced centered empty-state text with `NewListTypeCard` as the last grid item. Stores converted from `LazyColumn + ListItem` to `LazyVerticalGrid` with `StoreCard` and `NewStoreCard`, matching the Collections `OutlinedCard` pattern.

## [0.25.44] — 2026-05-17

### Fixed

- **Stores `TopAppBar` back button (Android):** `ShoppingStoreListScreen` was always showing a back arrow regardless of the `showBackButton` parameter.
- **Stores FAB removed (Android):** Replaced `FloatingActionButton` with an `IconButton` in `TopAppBar`, matching `DESIGN.md` (no FABs).

## [0.25.43] — 2026-05-17

### Changed

- **Cross-section swipe for Lists and Tasks (Android):** `ShoppingListScreen` and `MaintenanceScreen` now support `onSwipeLeft` / `onSwipeRight` callbacks wired to the outer `HomeScreen` `HorizontalPager`, enabling edge-swipe section navigation consistent with Collections.

## [0.25.42] — 2026-05-17

### Fixed

- **Collections "All" tab hidden when empty (Android):** An early-return guard bypassed the pager when `collections` was empty, hiding the tab strip. The All tab (with the New Collection card) now renders unconditionally.

## [0.25.41] — 2026-05-17

### Added

- **Stores as a dedicated bottom nav section (Android):** Stores (index 3) inserted between Lists and Tasks in `HOME_SECTIONS`. Tasks shifted to index 4, Alerts to 5, Settings to 6. The Home Jump-To grid updated accordingly.

## [0.25.40] — 2026-05-17

### Changed

- **Pull-to-refresh on all Tasks tabs (Android):** Replaced centered `CircularProgressIndicator` items on Chores, My Tasks, and Scoreboard tabs with `PullToRefreshBox`, consistent with Collections and Lists.

## [0.25.39] — 2026-05-17

### Fixed

- **Chores spinner never clearing (Android):** Wrapped `getAlerts()` in `withTimeout(15_000L)` so the spinner clears within 15 seconds if the server is unreachable.
- **Lists empty state missing (Android):** Added `no_lists` string and guidance text to `ShoppingListScreen` page 0 when no list types exist.

## [0.25.38] — 2026-05-17

### Changed

- **Unified `AppBar` design for Tasks and Lists (Android):** `MaintenanceScreen` replaced `OutlinedButton("Refresh")` with an `IconButton` and removed the `FloatingActionButton`; context-sensitive `+` button in AppBar (Chores → new chore dialog, My Tasks → new task dialog). `ShoppingListScreen` AppBar `+` is context-sensitive (page 0 opens list wizard; page 1+ opens add-item dialog). All three index screens (Collections, Lists, Tasks) now use a consistent `TopAppBar + IconButton` pattern with no FABs or text buttons.

## [0.25.37] — 2026-05-17

### Added

- **Inline chore creation (Web):** Tasks page Chores tab now has an inline create form (collection picker, name, interval, notes; `POST /collections/{id}/chores`). Added `tasks.new_chore_button` locale key to all 7 languages.
- **Scoreboard tab (Android):** `MaintenanceScreen` gains a Scoreboard tab showing a ranked list with medals, achievement badges, and breakdown counts. Added `ScoreboardEntryDto` and `getScoreboard()` API call.

## [0.25.36] — 2026-05-17

### Changed

- **Nav order (Android):** Swapped Alerts and Tasks — order is now Home > Collections > Lists > Tasks > Alerts > Settings. Home Jump-To tile indices updated to match.
- **New chore dialog (Android):** `+` FAB on the Chores tab opens `NewChoreDialog` (collection picker, name, optional repeat interval, optional notes).

## [0.25.35] — 2026-05-17

### Added

- **My Tasks create/complete/delete flow (Android):** Full `NewTaskDialog`, `TaskCard` with complete/delete actions, `StandaloneTaskDto` / `CreateTaskBody` DTOs, and `getTasks` / `createTask` / `completeTask` / `deleteTask` API endpoints. Replaced the previous stub.
- **Home grid expanded (Android):** 2×3 grid with all 5 nav sections (Collections, Lists, Tasks, Alerts, Settings) with correct pager indices.
- **Chores "Manage chores →" link (Android):** `TextButton` on each chore alert card deep-links to the collection's Chores tab via `HomeScreen → MaintenanceScreen → AlertCard`.

### Fixed

- **Web My Tasks 429 error (Web):** Shows a friendly message instead of a raw HTTP status code when the rate limiter is hit.

## [0.25.34] — 2026-05-17

### Changed

- **Stores and Settings nav dropdowns (Web):** Navigation bar gains dropdown menus for Stores (list of store names) and Settings (Appearance, Notifications, Account subsections).
- **Filter row alignment (Web):** Collection item filter rows align correctly with the content grid on narrow viewports.

## [0.25.33] — 2026-05-17

### Fixed

- **Android version drift:** `versionCode` corrected to 104 / `versionName` to `"0.25.33"` for Obtainium detection (was stuck at values from v0.25.31).

## [0.25.32] — 2026-05-16

### Added

- **Standalone `/alerts` route (Web):** Alerts moved to their own page; the bell dropdown "View all" link points to `/alerts`.
- **Tasks nav dropdown (Web):** Tasks nav link converted to a dropdown with Chores / My Tasks / Scoreboard sub-links.
- **"+ New list" shortcut (Web):** Added to the Lists nav dropdown.

### Fixed

- **Collections preset picker icons (Web):** Icon lookup was using `r.id` as the key instead of `r.slug`, causing all preset icons to fall back to the default.
- **Nav vertical alignment (Web):** `nav-lists-trigger` inherited correct `font` and `line-height` so the trigger button aligns with other nav items.

## [0.25.31] — 2026-05-12

### Fixed

- **About screen compile error (Android):** `fillMaxWidth` import was accidentally dropped when removing the unused `fillMaxSize` import in v0.25.30, causing a build failure on CI. Import restored.

## [0.25.30] — 2026-05-11

### Fixed

- **About/Info page scroll doesn't reach bottom nav bar (Android):** The About, Settings, and Maintenance screens each have their own inner `Scaffold` nested inside the `HomeScreen` outer `Scaffold`. The inner Scaffolds were double-counting the bottom window inset (nav bar height), leaving a dead zone at the bottom of each scrollable screen. Fixed by setting `contentWindowInsets = WindowInsets(0)` on each inner Scaffold so the outer pager's bottom padding is solely responsible for nav bar clearance.

## [0.25.29] — 2026-05-11

### Fixed

- **Android 401 / session expiry (Android):** When the server returns 401 (expired token), the app now automatically clears the stored session and redirects to the login screen instead of showing a permanent HTTP 401 error on every screen.
- **About page cut off (Android):** The About/Info screen content was not scrollable, causing the bottom buttons to be clipped on smaller screens. The column is now vertically scrollable.

## [0.25.28] — 2026-05-11

### Fixed

- **Android version drift (corrective release):** `v0.25.27` tag was cut before the `build.gradle.kts` version bump landed, so the APK attached to that release still reported `0.25.25`. This release re-tags with the correct `versionCode = 99` / `versionName = "0.25.28"` so Obtainium and Settings → About both reflect the current version.

## [0.25.27] — 2026-05-11

### Fixed

- **Missing H1 headings on collection sub-pages (web):** Bundles, Chores, Locations, Members, and Templates sub-pages had no page-level `<h1>`. Each now renders a heading using the existing `collections.tab_*` i18n key.
- **Hardcoded inline styles on collection sub-pages (web):** `margin: 1rem 0` and raw `display:grid; gap:.5rem` inline styles replaced with token-aligned `margin-bottom: 1.5rem` and scoped CSS classes (`.member-form-row`, `.share-form-row`).
- **Missing `svelte-i18n` import in Templates page (web):** `$_` was used but not imported, causing a type error.
- **Android version drift:** `versionCode` bumped to 98 and `versionName` corrected to `"0.25.27"` (was stuck at `96` / `"0.25.25"` since two releases were incorrectly skipped for Android).

### Docs

- **Material 3 design contract (`docs/DESIGN.md`):** establishes M3 as the binding standard across web and Android. Covers design tokens, component vocabulary, page anatomy, cross-platform parity table, and a don'ts gallery.
- **AGENTS.md UI/UX Standards section:** six always/never rules enforce the design contract in future sessions.
- **AGENTS.md release procedure:** clarified that `build.gradle.kts` must be bumped on every release without exception.

## [0.25.26] — 2026-05-11

### Fixed

- **Healthcheck path (server/Docker):** `HEALTHCHECK` in `Dockerfile` and both Compose files corrected from `/healthz` (SPA fallback, returns 400) to `/api/healthz`. Containers now report healthy correctly.
- **Navigation list types hardcoded (web):** the nav sidebar had four static links (`/lists/groceries` etc.). It now fetches `GET /lists/types` on mount and after navigation, rendering only the user's actual list types dynamically.
- **Home tile and grocery-list redirect (web):** the Lists tile on the home page and the `/grocery-list` legacy route were redirecting to `/lists/groceries`. Both now go to `/lists`.
- **List item page hardcoded types (web):** `lists/[type]/+page.svelte` had hardcoded `VALID_TYPES`, `BACKING_COLLECTION`, `LIST_ICON`, and wish-list special-case branches. The page now fetches `UserListType` dynamically; all custom list type slugs work without code changes.
- **Lists home anatomy (web):** the Lists home page used a dashed outlined card as the create affordance, while Collections used a standard button above the grid. Both pages now follow the same M3 layout: `+ New <thing>` button above the content grid.

### Docs

- **Material 3 design contract (`docs/DESIGN.md`):** new file establishes Material Design 3 as the binding visual and interaction standard across web and Android. Covers design tokens, component vocabulary, page anatomy rules, cross-platform parity table, and a don'ts gallery of regressions caught in this release.
- **AGENTS.md UI/UX Standards section:** six always/never rules enforce the design contract in every future AI-assisted session.

## [0.24.0] — 2026-05-08

### Internal

- **Web toolchain bump:** Node 18 → 20 (dev host), Vite `6.4.2 → 8.0.11`, `@sveltejs/vite-plugin-svelte` `5.1.1 → 7.1.2`. No behaviour change; `npm run check` (0 errors) and `npm run build` both pass.
- **Android toolchain bump:** Compose BOM `2024.11.00 → 2026.05.00`, AGP `8.7.2 → 8.13.2`, Kotlin `2.0.21 → 2.3.21`, KSP `2.0.21-1.0.28 → 2.3.7`, Room `2.6.1 → 2.8.4`, Lifecycle `2.8.7 → 2.10.0`, Hilt `2.52 → 2.57.2`, hilt-navigation-compose/hilt-work `1.2.0 → 1.3.0`. Gradle wrapper `8.10.2 → 8.13`. Removed obsolete `ksp.useKSP2=false` workaround. Migrated `kotlinOptions { jvmTarget }` to `kotlin { compilerOptions { } }` DSL. Fixed `LocalContextGetResourceValueCall` lint error in `AboutScreen.kt`. Lint 0 errors, unit tests pass, debug APK assembles.

## [0.23.0] — 2026-05-08

### Internal

- **Web toolchain bump:** SvelteKit `2.8 → 2.59.1`, Vite `5.4 → 6.4.2`, `@sveltejs/vite-plugin-svelte` `4.0 → 5.1.1`. No behaviour change.
- **Icon bundle reduced 98% (web):** `Icon.svelte` now imports only the 27 icons used in the app instead of the entire lucide-svelte namespace. The `Icon.js` server chunk dropped from 9.1 MB to 153 kB; client-side JS transferred on first load is proportionally smaller.

## [0.22.3] — 2026-05-20

### Fixed

- **Empty section-toolbar buttons (web, regression):** the Templates / Locations / Bundles / Chores / Members icons in the collection-detail toolbar were rendering as blank squares because `$lib/Icon.svelte` used Svelte 5's deprecated `<svelte:component>` to render `lucide-svelte` v1.0.1 components, whose legacy `$$props` plumbing did not receive the forwarded props. `Icon.svelte` now renders the resolved component value directly (Svelte 5 idiom). All icons across the app now render as intended.
- **Lists table horizontal scroll (web, Wave 10-B regression):** the Lists tables (Groceries / Hardware / Home Goods / Wish List) regained a horizontal scrollbar in v0.22.0, contradicting the "no horizontal scroll" promise. The shared `DataTable` now uses `table-layout: fixed` (scoped to a `.lists-table` wrapper) so column width caps are honoured; brand cell is 9ch, item cell flex-grows with `min-width: 0`, category 10ch, qty 5ch, notes 18ch, actions 6rem. Edit/delete buttons are no longer clipped on viewports ≥ 768 px.

### Changed

- **Filters panel collapsed by default everywhere (web):** the unified `FiltersPanel.svelte` shell on Collections detail and Lists pages now starts collapsed at every viewport, instead of auto-opening on ≥ 1024 px. Look and behaviour are now identical across both pages: a single `Filters · N` chip with an active-count badge; the user opens the panel explicitly when they need it.
- **Collection Add-item card matches Lists pattern (web, Wave 10-A):** the collection-detail Add card no longer hides the form behind an outer "+ Add an item" `<details>`. The form is always visible (one row: category root + leaf + URL/ISBN/EAN/title input + Scan image + Add). Extra fields (creator, subtitle) remain in the inner "+ More options" details. Visual and behavioural parity with `/lists/[type]` is restored.

## [0.22.2] — 2026-05-20

### Added

- **Icon source enforcement (web, Wave 10-H):** all stray `<svg>` elements and Unicode glyph icons (`▴ ▾ ▲ ▼ ↑ ↓ ✕`) have been replaced with `<Icon name="…" />` from `$lib/Icon.svelte`. Affected components: `FilterBar.svelte` (list/grid view toggles), `FiltersPanel.svelte` (open/close caret), `DataTable.svelte` (sort-direction arrows), `ItemComments.svelte` (expand/collapse toggle), `ShoppingStoreManager.svelte` (close and aisle-move buttons).
- **`check-icons` script (web, Wave 10-H):** `web/scripts/check-icons.mjs` walks `src/**/*.svelte` and flags bare `<svg>` elements and Unicode glyph-icon characters. Run as `npm run check-icons`; wired into `npm run check` so it runs in CI automatically.

### Changed

- **Iconography rule added to AGENTS.md:** `$lib/Icon.svelte` is the sole source for icons on the web front-end; bare `<svg>` elements and Unicode glyph substitutes are banned and enforced by `npm run check-icons`.

## [0.22.1] — 2026-05-20

### Added

- **Templates two-step wizard (web, Wave 10-G):** the "New template" flow is now a two-step modal wizard. Step 1 picks a name and category (defaulting to the collection's default category). Step 2 is the custom fields editor with the Advanced JSON toggle. The community scraper registry is no longer shown upfront — it is accessible via a "Start from a scraper preset" link inside the wizard, opening a dedicated registry modal.
- **Linked-to badge on imported templates (web, Wave 10-G):** templates imported from the community scraper registry now show a small "Linked to: &lt;entry name&gt;" pill in the templates table so users can see which preset each template came from.
- **`scraper_id` on ItemTemplate (server, Wave 10-G):** a new nullable `scraper_id` column on `item_templates` stores the registry entry ID for templates imported via the registry. Alembic migration `0009_template_scraper_id` handles the upgrade. The field is exposed in `ItemTemplateRead`. Existing description-marker-based deduplication is preserved as a fallback.

## [0.22.0] — 2026-05-16

### Added

- **Lists — Brand + Notes columns (web, Wave 10-B):** the Grocery, Hardware and Home Goods tables now show Brand and Notes as separate columns alongside Item, Category and Qty. Brand text is small and muted; Notes truncates with an ellipsis. Column widths are capped so the table never scrolls horizontally.
- **Unified Filters panel (web, Wave 10-C):** a new `FiltersPanel.svelte` shell wraps both the collections detail page (search + sort + advanced filters) and the lists page. The panel shows a "Filters · N" chip with an active-count badge; clicking it collapses/expands the controls. Opens by default on ≥ 1024 px screens. Lists pages now have search (by name, brand, notes), sort (name / quantity / date / category) and a category filter — all applied client-side.
- **Collection sections icon toolbar (web, Wave 10-F):** the inner Templates / Locations / Bundles / Chores / Members tab strip is replaced by a compact horizontal icon toolbar. Each button opens a modal dialog containing the matching panel. Import and Export remain as direct links. Old sub-route URLs (`/collections/{id}/templates` etc.) now redirect to `/collections/{id}` via server-side 302s.
- **Stores top-level nav (web, Wave 10-E):** the Stores page is already a first-class nav destination between Lists and Maintenance; the inline "Manage stores" button has been removed from the Lists header.

### Changed

- **AdvancedFilters merged into FilterBar (web):** the separate `AdvancedFilters.svelte` component is retired; its controls (category, ownership, archived, tag chips) now live inside `FilterBar.svelte` which wraps the new `FiltersPanel` shell.

## [0.21.1] — 2026-05-07

### Fixed

- **Theme list now alphabetical (web):** the color theme picker in Settings is sorted A–Z (Blackboard, Blues, Cloud, Espresso, Gazette, Granite, One Dark, Paper, Passion, Tangible, Tron).
- **Collection filter controls no longer stack (web):** the Sort, Direction, and filter selects on collection detail pages now stay inline in a single row instead of expanding to full width and stacking vertically. Layout now matches the compact single-row style of the shopping list view.

### Added

- **Light and dark modes for every theme (web):** all 11 color themes now fully support the Light, Dark, and System mode toggle. Previously only the Tangible theme responded to the mode switch; the remaining themes were locked to a single appearance. Each theme now has a carefully crafted opposite variant that preserves its key accent color while adapting backgrounds, surfaces, borders, and text for legibility in the chosen mode. The swatch previews in Settings update in real time to show what the theme looks like in the currently selected mode.
- **Granite dark richer contrast:** the Granite dark variant's background is now noticeably deeper (`#1D2327` vs `#2C343B`) so it no longer looks washed out next to the darker themes.

## [0.20.3] — 2026-05-07

### Fixed

- **Lists view crash (web):** the `effect_update_depth_exceeded` infinite loop affecting the grocery/hardware/home goods/wish list views is now fixed. Same root cause as the v0.20.2 collections fix — `loadGen` was declared as `$state`, causing the load-trigger `$effect` to re-register it as a reactive dependency on every run.
- **Reactive effect over-triggering (web):** three `$effect` blocks in the collections detail and import pages that both read and wrote the same `$state` variable (leaf category selection clamping) now use `untrack()` on the read side, preventing a redundant extra evaluation on every root-category change.

### Fixed

- **Collections view crash (web, take 2):** the `effect_update_depth_exceeded` infinite loop was not fully resolved in v0.20.1. The `loadGen += 1` expression inside the `$effect` reads `loadGen` before writing it, registering it as a reactive dependency regardless of the `untrack()` wrapper added in v0.20.1. Changed `loadGen` from `$state` to a plain variable — it is a generation counter for async race protection only and never rendered, so it needs no reactivity.

## [0.20.1] — 2026-05-07

### Fixed

- **Collections view crash (web):** opening a collection no longer throws `effect_update_depth_exceeded` and renders a blank page. The `$effect` that reloads on collection-id changes was creating an infinite reactive loop by reading `loadGen` inside `load()` synchronously, which Svelte 5 tracked as a dependency. Wrapped the call in `untrack()` to break the cycle.

## [0.20.0] — 2026-05-07

### Fixed

- **Tab state race condition (web):** switching collection or list tabs quickly no longer causes items from the previous tab to flash into the new tab. Each load now uses a generation counter so stale in-flight responses are silently discarded on arrival.
- **Horizontal scroll eliminated (web):** long item titles no longer push list rows wider than the viewport on small screens. Titles truncate with an ellipsis; table and card containers are constrained to the viewport width.
- **Logo visibility in dark mode (web):** the shield icon in the header now has a subtle drop-shadow so it reads clearly against the granite-dark and tangible-dark header surfaces.

### Changed

- **Category-aware secondary text (web):** the second line on item cards and table rows now adapts to the collection type — Artist for Music, Author for Books, Brand for Groceries/Hardware/Home Goods, and Subtitle/Creator for everything else. A shared `itemDisplay.ts` helper provides consistent output across the grid and table views.
- **Collapsible add and filter controls (web):** the Add Item form and the Advanced Filters panel are now collapsible. On mobile they start closed (saving screen space); on desktop (≥ 1024 px) they start open. Both retain the toggle state as you interact.
- **Button component (web):** `Button` now accepts an optional `icon` prop that renders a leading icon before the label, and a `form` prop for submit buttons placed outside their form element.
- **Modal component (web):** `Modal`'s `open` prop is now properly `$bindable` in Svelte 5, so `bind:open` works correctly without type errors.



### Changed

- **Item editor redesign:** the inline row edit form is replaced by a slide-over panel that opens from the right (full-screen on phones). All fields — title, creator, series/subtitle, condition, quantity, purchase date, and consumable date fields — are grouped in a scrollable panel with a sticky Save/Cancel footer. The panel closes when you press × or click the backdrop.
- **Tabbed collections view:** `/collections` now has a horizontally scrollable tab strip — an "All" tab for the overview grid and one tab per collection. Swiping left/right (or pressing arrow keys) navigates between tabs. The last-visited tab is persisted in `localStorage`; direct `/collections/{id}` links still work as deep links.
- **Tabbed lists view:** `/lists` now shows a tab strip for Groceries, Hardware, Home Goods, and Wish List. Navigating to `/lists` automatically redirects to the last-viewed list type. Swipe and arrow-key navigation work the same as the collections tabs. Deep links (`/lists/{type}`) remain valid.
- **Accessibility improvements:** touch targets raised to 44 px minimum everywhere; date/time values wrapped in `<time datetime="ISO">` elements in item badges, chores, maintenance due-dates, and audit-log timestamps; modal footers stack vertically on narrow viewports (≤ 480 px) so buttons never clip off-screen.

## [0.18.16] — 2026-05-06

### Fixed

- **Search: false positives eliminated.** The "all characters present" fuzzy heuristic (score 25) that caused unrelated items like "Gentle Body Wash" to appear when searching "bread" has been removed. Only exact and substring matches are now returned.
- **Search: shopping list items now included.** Searching from the Home screen now also returns unpurchased shopping-list entries (Groceries, Hardware, Home Goods, Wish List). Results from the list link directly to that list tab rather than to a collection item.

### Changed

- **Home search UX (web + Android):** Search box gains an ✕ clear button when text is entered. The filter row is consolidated to one line: the "Archived" checkbox anchors to the left, the field selector right-justifies. The "Jump to" shortcuts are hidden while search results are visible, placing results immediately below the filter row.

## [0.18.15] — 2026-05-06

### Changed

- **Web lists pages: Wave 4 component migration complete.** Each list type (Groceries, Hardware, Home Goods, Wish List) now uses the shared component library: the add form shows only name and category in the primary row with brand, notes, quantity, unit, URL, and priority in a collapsible "More options" section; the item table uses the reusable DataTable with a mobile card fallback; the edit form opens in a Modal; and the delete action requires confirmation via ConfirmDialog instead of a browser-native `confirm()` dialog. The store manager's delete-store action likewise uses ConfirmDialog.

## [0.18.14] — 2026-05-06

### Changed

- **Web nav: profile name now leads with a person icon** so every entry in the top bar carries an icon (Home, Collections, Lists, Maintenance, Settings, Profile).
- **Web alerts dropdown:** every alert now shows a per-kind leading icon next to the title (wrench for maintenance, sparkles for chores, clock for use-by, package-x for low-stock) and the due date is wrapped in a real `<time datetime>` element so screen-readers and copy-paste work correctly.
- **Roadmap Phase 14 status snapshot** updated to reflect what is actually shipped (Waves 1, 2, 3, 5 done; Wave 4 mostly done; Waves 6, 7, 8 still pending).

## [0.18.13] — 2026-05-06

### Changed

- **Web Home: search box decluttered.** The placeholder now reads just "Search" since the dropdown beside it already says which field is being searched. The "Search in" dropdown and the "Include archived items" toggle moved underneath the search box (no more wrapping in the narrow column), and the jump-to tiles now show the same icons used on the Android bottom navigation (folder, list, wrench, upload, settings) so the two surfaces visually match.
- **Web nav: Home, icons, and All Lists.** A Home link with a house icon is now the first menu item, every nav entry has a matching icon (Collections / Lists / Maintenance / Settings), and the Lists dropdown gains an "All Lists" entry that opens a new `/lists` landing page mirroring "All Collections".

### Added

- **Android Home tab: jump-to icon tiles** for Collections, Lists, Maintenance, and Settings. Tapping a tile swipes to that section so the search hub mirrors the bottom navigation and gives one-tap access from the search results.
- **Roadmap Phase 14, Wave 8:** tabbed swipeable Collections and Lists pages on web for parity with the Android client (touchscreen-laptop friendly).

## [0.18.12] — 2026-05-06

### Added

- **Home page with universal search** (web `/`, Android Home tab). One search box hits every accessible collection at once with a "Search in" dropdown (All / Title / Brand / Category / Notes / Barcode / Serial). Result rows show whether the item is Owned, Wishlist, Depleted, or Archived so a flea-market lookup instantly answers "do I already have one?". Includes archived/disposed items by default so previously-sold items still surface.
- **Empty-state quick add**: when nothing matches, a button opens a small dialog to drop the search term into a chosen collection (optionally as a wishlist item) without leaving Home.
- **Server: `POST /items` falls back to the collection's `default_category_slug`** when no `category` or `category_id` is supplied, so quick-add flows don't have to know the category up front.

### Changed

- **Web: collections list moved from `/` to `/collections`.** The header brand link and the Collections menu now route there; the new Home page lives at `/`. Existing `/collections/{id}` deep-links and "Add Collection" links still work.
- **Android: bottom nav gains a Home tab** as the leftmost section. Existing tabs (Collections, Lists, Maintenance, Settings, About) shift one position to the right.

## [0.18.11] — 2026-05-06

### Changed

- **Android: Pantry / Collections rows now show brand and category, matching the shopping list.** Both the list and grid views display "Brand · Category" as a colored subtitle (or just brand, or just category, or the item subtitle / first line of notes if neither is set), so the same item reads the same way in either screen.
- **Android: Item editor field order now mirrors the shopping list editor.** Brand, Title, Subtitle, Notes, then Quantity (paired with Condition), then Location, Purchase price, Current value, and Currency. Editing the same item from either surface now starts with the same field on top.
- **Android: Lists toolbar gained the same Image and Tile/List icons as Collections.** Tap the picture icon to pick a photo from your gallery and have the barcode decoded and looked up; tap the grid icon to switch the list to a 2-column card view (and back). Aisle group headers span the full width in grid mode.

## [0.18.10] — 2026-05-06

### Fixed

- **Brand icons no longer ship with a white background around the shield.** The previous v0.18.9 assets were trimmed but the source PNG had an opaque white surround, which showed as a white square halo behind the shield silhouette in the web favicon, the PWA icon, and the Android launcher / adaptive icon. The white is now flood-filled to transparent in all derived assets (web favicons, `icon-192/512.png`, all five mipmap densities of `ic_launcher`, `ic_launcher_round`, `ic_launcher_foreground`, and `ic_launcher_monochrome`).

## [0.18.9] — 2026-05-06

### Changed

- **Brand refresh.** New shield-and-box logo and color palette (charcoal #2C343B / teal #1B8A74 / #22A88E) across the web UI, browser favicons, and Android launcher / adaptive / themed icons. The default `tangible-light` and `tangible-dark` themes now use the brand teal as the accent color. The web header and the login / register screens display the new logo. The repo README leads with the full wordmark.

## [0.18.8] — 2026-05-06

### Added

- **Android: Grid view toggle on the Collections tabs.** Each tab can now switch between a list and a 2-column grid; selection is per-session. Grid cards show category, title, quantity, and the same edit / add-to-list / delete row icons as the list view.
- **Android: Photo-as-barcode picker on the Collections tabs.** A new image icon next to the camera-scan button lets you pick a photo from your gallery; ML Kit decodes the barcode, looks it up via the server's barcode adapter, and pre-fills the new-item title.

## [0.18.7] — 2026-05-06

### Added

- **Android: Per-collection toolbar on the Collections tabs** with edit collection, delete collection, scan barcode, and add item icons. Replaces the legacy collection detail screen.

### Fixed

- **Android: Shopping list orphaned “moved-from” entries can now be deleted.** Tapping the trash icon on a depleted-link feed entry clears the depleted flag on the underlying item, removing it from the synthetic feed without affecting the collection. Pre-existing entries from before v0.18.6's Move fix can finally be cleared.

### Removed

- **Android: Legacy `CollectionDetailScreen`** and its `collection/{id}` route. All of its features (search, edit, delete, add item, scan, item-row actions, add-to-list with copy/move) now live on the Collections tabs. Tapping a depleted-link shopping entry no longer navigates anywhere; use the trash button instead.

## [0.18.6] — 2026-05-06

### Fixed

- **Android: “Move” on a collection item now actually deletes it from the collection** instead of marking it depleted. The result is a normal independent shopping list entry, not a back-link feed entry with a navigation arrow.
- **Android: Shopping list auto-refreshes when the screen returns to the foreground** — items added from Collections via Copy or Move appear immediately, no manual pull-to-refresh required.

### Changed

- **Android: Shopping list rows redesigned to match the Collections list style** — dense `ListItem` rows with a single divider between items, brand and category shown as a secondary line, action icons (delete + check) inline on the right. Visual language is now consistent across Collections tabs and every shopping list type.

## [0.18.5] — 2026-05-06

### Fixed

- **Android: Brand, notes, and quantity now carried over when adding a collection item to the shopping list** — previously only the item name and category were copied; brand (e.g. "Hannaford") was silently dropped.

### Changed

- **Android: "Add to shopping list" dialog now offers Copy or Move** — the confirmation dialog has three options: **Cancel**, **Copy** (adds to the shopping list, item stays in the collection unchanged), and **Move** (adds to the shopping list and marks the collection item as depleted, indicating it has been used up and needs restocking). Works for any collection type — useful for pantry items, disposable batteries, cleaning supplies, etc.

## [0.18.4] — 2026-05-06

### Added

- **Android: Search bar on each Collections tab** — an inline `OutlinedTextField` above the item list filters items by title as you type, with an ✕ clear button.
- **Android: Per-row action icons on item rows** — each item in the Collections tabs now shows a pencil (edit), shopping-cart (add to shopping list), and trash (delete) icon on the right.
- **Android: Long-press item to edit directly** — long-pressing any item row opens the item detail screen in edit mode, skipping the view-only screen.
- **Android: Confirm before deleting an item** — tapping the trash icon shows an `AlertDialog` asking for confirmation before the item is permanently removed.
- **Android: Confirm before adding an item to the shopping list** — tapping the shopping-cart icon shows an `AlertDialog` before the item is added.

## [0.18.3] — 2026-05-06

### Fixed

- **Android: Tapping an item in the Collections tab now opens the item** — previously tapping any item row navigated to the collection detail screen instead of the item detail screen, making the tap appear to do nothing. System back then skipped the item entirely.
- **Android: Back press dismisses dialogs before navigating away** — on gesture navigation, pressing back while the "Add item" or barcode candidate dialog is open now dismisses the dialog rather than popping the screen. This prevents the "new item dialog appears twice" issue.

## [0.18.2] — 2026-05-06

### Fixed

- **Android: Collections + button moved to toolbar** — the add-collection button is now an icon in the top bar on the Collections tab (both the empty-state and the tabbed pager views), matching the Lists tab style.
- **Android: Pencil icon on item rows for direct edit** — tapping an item still opens the read-only detail view; a new pencil icon next to the trash icon jumps straight into edit mode without having to tap through the detail view first. Works in both list and grid view.
- **Android: Add item button moved to toolbar** — the + button to add an item to a collection is now in the top-right toolbar rather than a floating action button.

## [0.18.1] — 2026-05-06

### Fixed

- **Android: What's New renders properly** — the changelog modal now formats `# Heading` as a title, `## Version` headers as section headers, `- bullet` as bullet points, and strips `**bold**` markers instead of showing them literally.
- **Android: Item edit shows photos and NFC on one screen** — tapping the pencil on an item now shows the photo strip, all editable fields (including Brand), and the NFC write button together. Previously photos and NFC were only visible in the read-only detail view.
- **Android: Brand field editable on item** — the Brand field (stored in item attributes) is now shown and editable on the item edit screen.
- **Android: Collections + button moved to toolbar** — the add-collection button is now an icon in the top bar (matching the Lists tab style) rather than a floating action button.

## [0.18.0] — 2026-05-05

### Added

- **Offline-first shopping list** — checking off items (purchase and restock) now works with no cell signal. Actions are written to a local `pending_mutations` queue and replayed automatically by `MutationDrainerWorker` (WorkManager, CONNECTED constraint) the moment the device reconnects. The `Idempotency-Key` header prevents duplicate lots on server-side replay. An offline banner appears at the top of the shopping list when the device has no internet.

## [0.17.36] — 2026-05-05

### Fixed

- **Android: Pantry / Collections shows items again** — items created server-side without a category (notably items created by the shopping-list "purchase" flow) crashed the Android JSON parser, causing the entire collection to render as "No items yet" until a manual `clear app data`. The item DTO now treats the category as optional.
- **Web: Templates page shows readable category names** — the community scraper presets and template list now display the human category path (for example `Pantry › Pantry Item`) instead of the raw `spices.pantry` slug, removing the "why does it say spices?" confusion.

## [0.17.35] — 2026-05-05

### Fixed

- **Android: shopping check now syncs to server** — tapping the checkmark on a shopping list entry now immediately marks it purchased on the server (matches the web's "Mark purchased" button) and the row disappears from every device. The local-only "Checked" section and the separate "Move all to pantry" button have been removed; failures roll the row back and surface the error.
- **Android: pull-to-refresh on empty Lists and Collections** — the gesture now works even when the list is empty or still loading. The empty/loading placeholders are wrapped in a scrollable container so `PullToRefreshBox` receives the gesture.
- **Web: Pantry / Items list view declutter** — each row no longer shows a giant empty photo placeholder and a Comments toggle. Photos and comments remain available in the grid/card view and inside item edit.
- **Web: bulk action toolbar** — the long row of bulk actions is now hidden until you select at least one item, then appears as a sticky bottom bar with sized inputs instead of a vertical tower at the top of the page.
- **Templates: Open Food Facts Pantry preset uses correct category** — was bound to the non-existent slug `spices.pantry_item`; now bound to `spices.pantry`.

### Added

- **Barcode coverage for non-food household items** — added `OpenProductsFactsBarcodeAdapter` (cleaning supplies, hardware, kitchenware, electronics) and `OpenBeautyFactsBarcodeAdapter` (cosmetics, toiletries) alongside the existing OpenFoodFacts adapter. All three are no-API-key sister projects, so non-food UPCs (Brasso, body wash, etc.) now resolve.

## [0.17.34] — 2026-05-05

### Fixed

- **Android: Collections pull-to-refresh** — pull-down on the item list now works. `PullToRefreshBox` was previously nested inside `HorizontalPager`, which intercepted the initial touch before direction was known; it is now hoisted above the pager.
- **Android: Collections title bar** — the top app bar always shows "Collections" instead of the currently selected tab name (the active tab is already highlighted in the tab strip).
- **Android: Collections title-bar swipe** — swiping the title bar left or right navigates to the next/previous top-level section (Grocery List, Maintenance, etc.), matching the behaviour of the navigation bar.
- **Server: grocery purchase always creates pantry item** — purchasing an ad-hoc shopping entry now always creates an inventory item in the target collection, even when no category could be resolved from the barcode or collection default. Previously the item was silently discarded in that case. A new migration (`0007`) makes `items.category_id` nullable to allow category-less items.

## [0.17.33] — 2026-05-05

### Web UI redesign (Phase 14)

- **New design system** — 11 colour palettes (pick in Settings > Appearance), a unified token set (`--bg`, `--surface`, `--accent`, etc.) used across every page, and a Lucide icon library replacing emoji and inline SVGs throughout.
- **Shared component library** — Button, IconButton, FormField, Alert, Badge, Card, EmptyState, Modal, ConfirmDialog, Spinner, and PageHeader components replace ad-hoc duplicated markup across all pages.
- **Settings redesigned** — settings are now split into a sidebar-nav layout with five sub-routes: Account, Appearance, Security (API tokens + sessions + 2FA), Notifications, and About.
- **Collection sub-route layout** — collections/[id] pages (Items, Locations, Maintenance, Chores, Bundles, Templates, Members) share a single tab-nav layout; the collection header and breadcrumbs appear once and scroll away together.
- **Maintenance** — urgency sort (Critical first), per-severity icons, and an EmptyState "all-clear" banner when nothing needs attention.
- **Locations** — per-kind icons (home / building / door / pin / box), tree role for accessibility, ConfirmDialog for deletes.
- **Chores** — overdue left-border highlight and circle-alert icon; snooze uses a Modal; ConfirmDialog for deletes.
- **Bundles** — per-asset-kind icons (book / image / config / wrench / nut / file), Modal for editing, ConfirmDialog for deletes.
- **Templates** — ConfirmDialog replaces inline modal; label-for wired to name input.
- **Members** — ConfirmDialog replaces three inline modals; audit log, share links, and invitations tables all scroll horizontally on mobile.
- **Lists (shopping)** — per-type icon in the heading; store selector uses lucide icon instead of emoji.
- **Import** — radio-card mode selector; Alert component for results and errors.
- **Comments** — ConfirmDialog for delete; `<time>` elements for timestamps; reply icon.
- **Photo gallery** — lucide icons for lightbox nav / close; nav repositioned for mobile.
- **Shopping store manager** — lucide close icon; aria-labels on move buttons; stacked layout on mobile.
- **Mobile polish** — all tables wrapped in horizontal-scroll containers; `main` padding reduced on narrow viewports; header icon-buttons meet the 44 px touch-target minimum.
- **Accessibility sweep** — `aria-selected` on treeitem nodes; `for`/`id` wired for all labels in the import and templates pages; skeleton `<h1>` has `aria-label`; `svelte-check` 0 errors.
- **i18n** — all 7 locales updated; `settings.palette_label` backfilled in es/fr/it/ja/zh.

## [0.17.32] — 2026-05-05

- **Fixed: marking a shopping item purchased now creates the pantry item** — previously, checking off an ad-hoc shopping entry (one not tied to an existing item) only marked the entry purchased; nothing was added to the destination collection, so groceries effectively disappeared. Now an item is created in the entry's collection with the name, quantity, notes, and brand from the shopping list, using the entry's category (or the collection's default category) for placement.
- **Android: Add Item in a category-defaulted collection now pre-selects that category** — collections created with a default category (for example, a Pantry pre-set to Groceries) now correctly pre-select the root category in the Add Item dialog, instead of forcing you to pick one every time.
- **Android: Collections are now swipeable tabs** — the Collections section shows one tab per collection, like the Lists section. Swipe between tabs to flip through your collections without leaving the home screen; tap any item (or "Add item" in an empty collection) to open the full collection view for advanced editing. The "+" button still creates a new collection.

## [0.17.31] — 2026-05-05

- **Android: swipe the nav bar to change sections** — dragging left or right on the bottom navigation icons now slides between sections (Collections, Lists, Maintenance, Settings, About), in addition to tapping a specific icon.
- **Android: inner tab swipe no longer hijacked by outer pager** — the outer section pager no longer intercepts horizontal swipes in the content area. In the Lists section, swiping left/right now moves between Groceries, Hardware, Home Goods, and Wish List tabs as expected; section changes happen via the nav bar.
- **Android: store sort icon moved left of scan icon** — top-bar icon order is now Store, Scan, Add (+) from left to right.

## [0.17.30] — 2026-05-05

- **Android: scan and add buttons moved to the top app bar** — the floating barcode scan and add (+) buttons no longer overlap the per-row check/edit/delete buttons on the right side of each list item. Both actions are now icon buttons in the top app bar next to the store sort icon.

## [0.17.29] — 2026-05-05

- **Android: shopping list rows show brand instead of collection name** — the second-line label on each list row now shows the brand when present (the collection is implied by the list type, so it was redundant). Depleted-item entries still fall back to the collection name when no brand is set so the navigation hint is preserved.

## [0.17.28] — 2026-05-05

- **Fixed: brand not saved when adding shopping list items** — the create endpoint silently dropped the `brand` field on insert, so brands captured from barcode scans (or typed manually) disappeared as soon as the item was added. The brand is now persisted and returned on the create response, edit dialog, and feed.
- **Android: shopping list create response includes brand** — the read DTO now carries the `brand` field so the client sees it in the immediate response without waiting for the next feed refresh.

## [0.17.27] — 2026-05-05

- **Android: Remove blank space below nav bar icons** — the gap between the bottom navigation icons and the system navigation bar is eliminated by zeroing the NavigationBar's internal window insets.

## [0.17.26] — 2026-05-05

- **Android: Restore section titles** — page titles (Collections, Lists, Settings, About) are shown again; only the redundant text labels below the nav bar icons were removed.

## [0.17.25] — 2026-05-05

- **Android: Icon-only bottom navigation bar** — labels removed from the nav bar so the bar is more compact; icons remain with accessibility content descriptions.
- **Android: Removed redundant section headers** — the title bar ("Lists", "Settings", "About") is no longer shown when a screen is embedded in the swipeable pager, eliminating the blank space gap between the nav bar and the content.
- **Android: Matched scan and add FAB size** — the barcode scan button is now the same size and color as the Add (+) FAB.

## [0.17.24] — 2026-05-05

- **Android: Swipe to navigate between sections** — Collections, Lists, Maintenance, Settings, and About are now connected in a swipeable pager with a bottom navigation bar. Swipe left/right or tap the nav bar to move between sections instantly.
- **Android: Checked items list** — tapping the check button on a list item moves it to a "Checked" section at the bottom instead of immediately removing it. Each checked item shows an Uncheck button (move back to the active list) and a Move-to-Pantry button (commits it to the server). A "Move all to pantry" action commits all checked items at once.
- **Android: Scan button moved next to Add button** — the barcode scan button (camera icon) is now a small floating button directly above the main Add (+) FAB, keeping both actions together in the corner.

## [0.17.23] — 2026-05-06

- **Android: Barcode not-found feedback** — when a barcode scan returns no product match, the add-item dialog now shows a "Product not found — fill in the details below" hint so it is clear the form is blank intentionally.
- **Android & Web: Consistent field order in add/edit dialogs** — fields are now ordered Brand, Item Name, Category, Notes, Quantity across both the Android add and edit dialogs and the web add form and edit dialog.
- **New grocery category: Coffee, Tea & Drink Mixes** — added as a distinct category separate from Beverages (soft drinks/juices), available in all locales.

## [0.17.22] — 2026-05-05

- **Android: Fixed spinner stuck after editing an item** — after saving a name, category, brand, or notes change the item's loading indicator now clears immediately instead of staying until the next full navigation away and back.

## [0.17.21] — 2026-05-05

- **Android: Category picker in add and edit dialogs** — groceries, hardware, and home-goods items now show a category dropdown when adding or editing. Previously only hardware/home-goods had it in the add dialog, and the edit dialog had no category field at all.
- **Android: Brand field** — add and edit dialogs both include a Brand field. Barcode scans pre-fill it from product data (OpenFoodFacts `brands`), so scanning a product keeps the brand separate from any personal notes.
- **Web: Brand field** — add and edit forms on the shopping list now include a Brand field that is saved with the item.
- **Server: Brand stored on shopping list items** — new `brand` column on `grocery_items`; exposed on the feed and all CRUD endpoints.
- **Server: Title-case product names from barcode scans** — OpenFoodFacts frequently returns ALL-CAPS product names. The adapter now title-cases them on ingest so items like "CRISPY FRIED ONIONS" become "Crispy Fried Onions".
- **Server: Brand extracted separately from notes** — barcode lookups now return a dedicated `brand` field instead of stuffing brand text into the description/notes.

## [0.17.20] — 2026-05-05

- **Web: Fixed category field missing in edit dialog** — Svelte 5 schedules DOM updates as microtasks, so `editEntry` was not set by the time `showModal()` was called. Switched the category/wish-list conditional from `editEntry.list_type` to `listType` (always-available route param) to guarantee the field is rendered before the dialog opens.
- **Web: Graceful 502/503/504 handling** — the API client now retries gateway errors up to 3 times with 2.5 s intervals and shows a "Server is restarting" warning toast on the first attempt, so rolling Docker updates no longer surface a raw error to users.
- **Android: Shopping list offline cache** — the groceries/hardware/home-goods/wish-list feed is now backed by a Room table (`shopping_feed_cache`). After a successful load the results are written to the cache; on network failure the cached rows are returned so the list stays usable during a server restart. Room DB version bumped 5 → 6 (fallbackToDestructiveMigration in place).

## [0.17.19] — 2026-05-04

- **Web: Edit shopping list items** — ad-hoc list entries now have an Edit button that opens a dialog to update name, category, quantity, unit, and notes without removing and re-adding the item.
- **Web: Category aisle picker on edit** — the edit dialog shows the full preset aisle list for the list type (groceries, hardware, home goods) plus a free-text custom option.
- **Server: OpenFoodFacts category detection** — barcode lookups for food items now automatically map the product's category tags to a grocery aisle slug (e.g. whole milk maps to Dairy & Eggs), so the category is pre-filled when adding a scanned item.
- **Server: Barcode category memory** — after a user confirms or changes a category for a scanned barcode, the server records the association. Subsequent scans of the same UPC return a `hint_category_slug` so the app can pre-select the same aisle automatically.



- **Android: Fixed Add Item dialog crash on shopping lists** — restored a missing `if (showCollectionPicker)` wrapper and a missing `PullToRefreshBox` closing brace in `ShoppingListScreen`. Together they caused the 0.17.13 through 0.17.17 Android builds to fail. Locally verified with `lintDebug + testDebugUnitTest + assembleDebug` before tagging.
- **Android: Add Item dialog only shows the collection picker for the wish list** — previously the picker was always rendered (groceries, hardware, home goods all showed an empty dropdown). Now it only appears for the wish list when at least one collection exists.

## [0.17.17] — 2026-05-04

- **Android: Fixed shopping lists build error** — corrected a brace mismatch in the shopping list screen that caused the 0.17.15 and 0.17.16 Android builds to fail.

## [0.17.16] — 2026-05-04

- **Android: Fixed crash on shopping lists screen** — a stray brace from the swipe-tabs refactor caused the app to fail to build in 0.17.15; now corrected.

## [0.17.15] — 2026-05-04

- **Android: Pull-to-refresh fixed on shopping lists** — swiping down to refresh now works correctly on all tabs after the HorizontalPager swipe-tabs change in 0.17.14.
- **Android: Error notifications via Snackbar** — errors (network failures, save errors) are now shown as a brief Snackbar at the bottom of the screen instead of a centered text overlay that blocked interaction.
- **Android: Depleted-item visual cue** — inventory-feed items in shopping lists now show a small arrow icon next to the action buttons, making it clear that tapping navigates to the collection rather than opening an edit dialog.
- **Web: Toast notifications for API errors** — any API error now surfaces a brief toast notification at the bottom of the screen that fades out automatically, so no error is ever silently swallowed.

## [0.17.14] — 2026-05-04

- **Android: Barcode scan fills separate Notes field** — scanning a barcode now puts the product title in the Name field and the description (brand/category context) in an optional Notes field, so you can trim the name without losing brand details.
- **Android: Edit shopping list item** — tapping an item in any shopping list opens an edit dialog (name, quantity, notes) instead of navigating to its collection. Depleted-item feed entries still navigate to the collection as before.
- **Android: Fixed JSON error after adding item** — a mismatch between the server's create-item response and the app's expected shape caused an error overlay after every successful add. The app now parses the correct response type.

## [0.17.13] — 2026-05-04

- **Android: Help guide renders markdown** — the Help dialog now uses the same markdown renderer as the What's New changelog (headings, bullets) instead of showing plain text.
- **Android: Simplified Add Item dialog on shopping lists** — the Collection picker is gone from Groceries, Hardware, and Home Goods. Each list type automatically uses (or creates) its implied collection: Groceries → Pantry, Hardware → Workshop, Home Goods → Home.
- **Android: Wish List — collection picker** — when adding to the Wish List, a Collection dropdown lets you choose any existing collection. If you have no collections yet, the dialog instead shows a category-template row (Books, Movies, Games, Music, etc.) and a name field so you can create a new collection in the same step.
- **Android: Barcode scan loading indicator** — scanning a barcode now shows a "Looking up product…" overlay while the server request is in progress, instead of silently opening an empty dialog.
- **Android: Add Item dialog title reflects the active tab** — the dialog title now reads "Add Groceries item", "Add Hardware item", etc. rather than always saying "Add grocery item".
- **Admin: Barcode & Metadata Services panel** — the Settings → Admin tab now shows a table of active barcode/metadata adapters and which optional API-key environment variables expand coverage (Google Books, UPCitemdb, Discogs, TMDB, IGDB).

## [0.17.12] — 2026-05-04

- **Fix: Collections dropdown** — removed duplicate plus sign on "New collection" and opening one nav dropdown now closes the other.

## [0.17.11] — 2026-05-04

- **Redesigned navigation menu** — order is now Collections, Lists, Maintenance, Settings, Profile, Log out.
- **Collections dropdown** — the Collections nav item is now a dropdown that lists all your collections for one-click access, plus an "All Collections" link and an "Add Collection" shortcut that opens the new-collection wizard directly.

## [0.17.10] — 2026-05-04

- **Android: Renamed "Grocery List" to "Lists"** — the app bar title and navigation label now correctly reflect that the screen hosts all four list types, not just groceries.
- **Android: Fixed JSON parse error on lists screen** — the `/grocery/*` → `/lists/*` server redirect was producing a broken URL (missing `/api` prefix), causing OkHttp to follow to the wrong endpoint and Moshi to throw a "setLenient(true)" error. The redirect now preserves the full URL including path prefix.
- **Android: Formatted markdown changelog** — the in-app changelog dialog now renders `##`/`###` headings and `- ` bullet points instead of showing raw markdown text.
- **Android: Docs link in Help dialog** — the Help dialog now includes a "View full documentation" button that opens the Android user guide on GitHub.
- **Android: Category hidden on grocery/wish list** — the category field in the Add Item dialog is only shown for Hardware and Home Goods lists; groceries and wish list items no longer show an irrelevant category picker.
- **Android: Barcode scan for shopping items** — a scan button in the shopping list app bar opens the barcode scanner; after scanning, the product name is looked up via the server API and pre-filled in the Add Item dialog.

## [0.17.9] — 2026-05-04

- **Multi-type shopping lists** — the shopping list is now a hub for four list types: **Groceries**, **Hardware**, **Home Goods**, and **Wish List**. A new "Lists" dropdown in the nav lets you switch between them; each type has its own route (`/lists/groceries`, `/lists/hardware`, etc.).
- **Hardware & Home Goods categories** — 15 preset category chips for each new list type (fasteners, plumbing, paint, furniture, bedding, lighting, etc.) to keep items organised.
- **Wish List fields** — wish list items can include a link and a priority (Low / Medium / High). Marking an item "received" removes it from the list, the same as "purchased" for other types.
- **Auto-backing collection** — adding an item to Groceries, Hardware, or Home Goods silently creates the matching collection (Pantry, Hardware, Home Goods) if it does not already exist.
- **Android list tabs** — the Android Shopping screen now has four tabs at the top; switching tabs filters the feed to that list type.
- **MCP `list_shopping_items` tool** — AI agents can now query any list type via the MCP server using the optional `list_type` parameter.
- **Backward compatibility** — the old `/grocery/*` API paths continue to redirect to `/lists/*` for older clients.

## [0.17.8] — 2026-05-03

- **Internal refactor** — the shopping list module has been renamed from "Grocery" to "Shopping" throughout the codebase in preparation for expanding the list beyond grocery items. No user-visible behavior changes; the `/grocery/*` API paths continue to work via redirect for older Android clients.

## [0.17.7] — 2026-05-03

- **Test Connection buttons** — the Admin Settings page now has a "Test" button next to each integration API key (Discogs, TMDb, IGDB, Google Books, UPCitemdb) and a "Send test email" button in the Email / SMTP section so operators can verify credentials without leaving the settings panel.
- **Grocery list fixes** — the "No Pantry collection yet." banner is removed; Pantry is auto-created silently the first time you add a grocery item. Fixed a CSS bug where the banner used dark-mode colors in light mode.

## [0.17.6] — 2026-05-03

- **Full web i18n** — every visible English string across all pages and components is now translated through the locale system. French, German, Spanish, Italian, Japanese, and Chinese users see their language throughout the entire web app — collections, items, bundles, chores, locations, members, grocery list, import, share links, invitations, comments, and maintenance pages.
- **Alerts moved to bell icon** — upcoming maintenance alerts and low-stock notifications are now in a compact bell icon in the nav bar instead of a banner, keeping the page header clean.
- **Language preference in Settings** — the language picker has moved from the nav bar into the Settings page under a new User tab, alongside theme and account controls.
- **Grocery categories alphabetically sorted** — the preset category dropdown is now sorted A–Z for easier scanning regardless of language.
- **CI storage optimized** — Docker build cache switched to minimal mode and debug APK retention reduced to 3 days to stay within free storage limits.

## [0.17.5] — 2026-05-03

- **Android language picker** — choose from English, Français, Deutsch, Español, 日本語, 中文, or Italiano in Android Settings. The preference is stored locally, applied immediately, and synced to the server so the web picks up the same locale.
- **Android grocery & collection UX** — the category picker in Add Grocery Item is now a dropdown instead of a text field; aisle categories are listed one-per-line in alphabetical order; the Add Collection wizard uses a sorted single-column list.
- **Web i18n** — Maintenance, Grocery List, and Settings pages now use the locale system for all visible text.

## [0.17.4] — 2026-05-03

- **Grocery categories** — 17 preset categories (Produce, Bread, Bakery, Meat & Seafood, Deli, Dairy & Eggs, Frozen, Canned & Pantry, Pasta & Grains, Snacks, Beverages, Breakfast & Cereal, Condiments & Spices, Cleaning & Household, Health & Beauty, Pet Supplies, Alcohol) plus a Custom option. Bread and Bakery are intentionally distinct.
- **Grocery store manager** — create stores and assign aisles with category chip pickers so your shopping list can be sorted by aisle order. Accessible via the Stores button on the Grocery List page.
- **Android aisle category chips** — the Android aisle editor now shows FilterChip presets for all 17 categories instead of a free-text slug field.
- **Import moved to collection tab** — the Import link is removed from the top nav and is now a tab inside each collection's subnav. Opening it pre-selects the correct collection.
- **French and all-language i18n fix** — the Collections page was rendering hardcoded English strings regardless of language setting; all text now uses the locale system.
- **Japanese translations completed** — ja.json was missing all sections after the auth/profile block; full Japanese translations added for all UI sections.

## [0.17.3] — 2026-05-03

- **Chinese and Italian translations** — the web UI now supports Simplified
  Chinese (zh) and Italian (it), bringing the total to 7 languages (English,
  French, German, Spanish, Japanese, Chinese, Italian). The language picker in
  the navigation bar lists all seven; the preference is saved to the browser.
- **Updated documentation** — user guide, admin guide, Android user guide, and
  README updated to cover the grocery list (including store/aisle sorting),
  item comments, multilingual support, Admin Server Settings panel,
  site-wide 2FA enforcement, and the MCP server (AI assistant integration).

## [0.17.2] — 2026-05-03

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
