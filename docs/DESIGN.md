# Tangible Design Contract

**Status:** Active. This document is the binding visual & interaction
specification for Tangible across web and Android. Any contributor (human
or AI) must read this file before adding or restructuring any page,
component, or screen.

If a pattern is not in this document, it is not in the product. Extend the
document first, then the code.

---

## Foundation

Tangible follows **Material Design 3** (Material You) on both platforms.

- Reference: https://m3.material.io/
- **Android**: Material3 Compose components (`androidx.compose.material3`).
  Theme lives at `android/app/src/main/java/io/github/bradbrownjr/tangible/ui/theme/Theme.kt`
  and uses dynamic color (Material You) on Android 12+ with static fallback.
- **Web**: M3 component vocabulary expressed through SvelteKit components in
  `web/src/lib/components/`, styled with the design tokens in
  `web/src/lib/styles.css`. We do not pull in a full M3 web library; we
  match M3 behavior and shape with our own components.

We do not mix design languages. No Bootstrap, no iOS HIG, no Tailwind
component kits. Material 3 only.

### Design tokens (web)

Defined in `web/src/lib/styles.css`. Use these CSS variables; **never
hardcode** colors, spacing, radii, or font sizes.

| M3 role | CSS token | Notes |
| --- | --- | --- |
| Surface (background) | `--bg` | Page background |
| Surface container | `--surface` | Cards, sheets |
| Surface container high | `--surface-2` | Raised cards, tab strip background |
| Outline | `--border` | Component strokes, dividers |
| On-surface | `--text` | Primary text |
| On-surface variant | `--text-muted` | Secondary text, helper text |
| Primary | `--accent` | Filled buttons, FAB, selected tab indicator |
| Primary (hover/pressed) | `--accent-hover` | Hover/active states |
| On-primary | `--accent-contrast` | Text on filled-primary surfaces |
| Error | `--danger` | Error text, destructive actions |
| Tertiary (success) | `--success` | Confirmations, positive badges |
| Tertiary (warning) | `--warning` | Warning text, caution badges |
| Info | `--info` | Informational badges |

Spacing scale: `--space-1` (4px) through `--space-8` (64px). M3 uses an
8dp grid; our 4px base allows half-steps where needed.

Radius: `--radius-sm` (4px), `--radius-md` (8px), `--radius-lg` (12px),
`--radius-full`. M3 default for cards is 12px (`--radius-lg`); buttons are
typically `--radius-full` or `--radius-md`.

Elevation: `--shadow-sm` (M3 elevation 1), `--shadow-md` (elevation 3),
`--shadow-lg` (elevation 6+).

Typography: `--text-xs` through `--text-2xl`. Body text defaults to
`--text-base` (1rem). Page H1 is `--text-2xl`.

Tap target: `--tap-min` (44px). Every interactive element must meet this
on touch devices.

### Design tokens (Android)

`Theme.kt` provides a `MaterialTheme` with `ColorScheme`. Always read
colors from `MaterialTheme.colorScheme.*` and dimensions/typography from
`MaterialTheme.typography.*`. Never hardcode `Color(0xFF…)` outside
`Theme.kt`.

---

## Component vocabulary

For every UI affordance in the product, this is the canonical mapping.

| Affordance | M3 component | Web (Svelte) | Android (Compose) |
| --- | --- | --- | --- |
| Primary screen action on index pages ("create new X") | Inline New card — Outlined Card, dashed stroke, last item in grid | `<button class="card new-card">` | `OutlinedCard(border = dashed)` |
| Secondary action | Outlined Button | `Button.svelte` (variant `secondary`) | `OutlinedButton` |
| Tertiary / cancel / inline link | Text Button | `Button.svelte` (variant `text`) or `<button class="link">` | `TextButton` |
| Destructive action | Outlined or Filled Button (error color) + confirm | `Button.svelte` + `ConfirmDialog.svelte` | `OutlinedButton` + `AlertDialog` |
| Icon-only action | Icon Button | `IconButton.svelte` | `IconButton` |
| Item in a content grid | Filled Card (clickable) | `<a class="card">` or `SectionCard.svelte` | `Card(onClick = …)` |
| Container / panel grouping | Filled Card | `SectionCard.svelte` / `<div class="card">` | `Card` |
| Empty-state invite ("create your first thing") | Outlined Card with dashed stroke | `EmptyState.svelte` (variant `invite`) | `OutlinedCard(border = dashed)` |
| Status / count chip | Assist Chip / Badge | `Badge.svelte` | `AssistChip` / `Badge` |
| Inline form input | Outlined TextField | `FormField.svelte` | `OutlinedTextField` |
| Tabbed navigation | Primary Tabs | `Tabs.svelte` | `TabRow` |
| Bottom-aligned mobile nav | Navigation Bar | (web: top nav) | `NavigationBar` |
| Modal / blocking dialog | Dialog | `Modal.svelte` / `ConfirmDialog.svelte` | `AlertDialog` / `Dialog` |
| Transient feedback | Snackbar | `Toast.svelte` | `Snackbar` |
| Tabular data | Data Table | `DataTable.svelte` | (use `LazyColumn` of rows) |

When a new affordance is needed, add a row above and create the components
in the same PR. Do not invent variants in-page.

### Button labels

- New-card labels read `New <thing>` (e.g., `New collection`, `New list`).
  The `+` icon is rendered separately in the card; do not duplicate it in the label.
- Use sentence case, not Title Case. (`Mark as purchased`, not
  `Mark As Purchased`.)
- Destructive labels are explicit verbs (`Delete`, `Remove`), never `OK`
  or `Yes`.

---

## Page anatomy

Every **index page** (any route that lists a collection of things) follows
this structure, in this order:

1. **H1 page title** — single `<h1>{$_('section.title')}</h1>`.
2. **Wizard / form region** — when a create action is in progress, the
   wizard or form appears *above the grid* (not replacing it).
3. **Content region** — a `.presets` / `.grid` of filled Cards, followed
   by a single **New card** as the last item (see below). One of:
   - Loading: `<p class="muted">{$_('common.loading')}</p>`
   - Otherwise: always render the grid (even when empty) so the New card
     is always visible.

**New card** — The canonical create affordance on index pages. Always the
last item in the grid. Use `<button class="card new-card">` (dashed
`OutlinedCard`) with a `+` icon and a `New <thing>` label. There is no
separate top-of-page button. This pattern matches Android's `OutlinedCard`
with dashed border as the last grid item.

```html
<button type="button" class="card new-card" onclick={openPicker}>
    <Icon name="plus" size={24} />
    <span>{$_('section.add_button')}</span>
</button>
```

```css
.new-card {
    border-style: dashed;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 0.5rem; cursor: pointer;
    color: var(--accent); background: transparent;
    min-height: 7rem; font-size: 0.875rem;
}
.new-card:hover { background: color-mix(in srgb, var(--accent) 8%, transparent); border-color: var(--accent); }
```

**UX levels — index vs. detail:**
- Index page New card → creates a new top-level thing (collection, list, store).
- Detail page inline form → adds an *item inside* an existing thing.
These are on different routes; there is no visual ambiguity.

**Preset/category picker grid** — When a wizard step presents a grid of
selectable category or preset cards (`.presets`), always use
`align-items: start` on the grid container and `justify-content: flex-start`
on each `.preset`. This keeps every card's content anchored to the top edge,
regardless of description length. Do **not** use `align-items: stretch`;
stretching shorter cards to match their row's tallest neighbor creates empty
whitespace below the content, causing visual bouncing and jaggedness as the
eye tracks across rows.

**Canonical reference:** `web/src/routes/collections/+page.svelte`. When in
doubt, make the new page look like Collections.

### Detail pages

Every **detail page** (any route showing a single item / collection) follows:

1. Back/breadcrumb.
2. H1 of the item's name; optional subtitle in `<p class="muted">`.
3. Toolbar: filters / search / sort (use `FiltersPanel.svelte`).
4. Content (table, grid, sections of cards).
5. Item-add affordance lives **inside the content region** (an inline form
   above the table or list), not as a top-level button — the page-level
   primary action is "edit/share this collection," not "add an item."

**Canonical reference:** `web/src/routes/collections/[id]/+page.svelte`.

### Android: status / nav bar icon color

Always sync icon color with the active theme via a `SideEffect` in `MainActivity`:

```kotlin
SideEffect {
    val controller = WindowCompat.getInsetsController(window, window.decorView)
    controller.isAppearanceLightStatusBars = !dark
    controller.isAppearanceLightNavigationBars = !dark
}
```

Where `dark` is derived from the current `MaterialTheme.colorScheme.isLight` or the resolved palette mode. This must be updated whenever the theme changes so dark themes get white icons and light themes get dark icons. **Never** rely on the system default — it may not match the app palette.

### Form fields: required vs. optional

Never append `(optional)` to a field label — it bloats the label string and causes word-wrap in compact dialogs. Instead:

- **Required fields** — append ` *` to the label string (e.g., `"Chore name *"`).
- **Optional fields** — plain label only (e.g., `"Notes"`, `"Repeat every N days"`). Optionality is implied by the absence of `*`.

This applies to both Android (`strings.xml` hint strings) and web (`OutlinedTextField` / `<label>` text in locale JSON). On the web, the `*` is part of the translated string, not added in template markup.

---

### Android: `OutlinedTextField` height

The `OutlinedTextField(value, onValueChange, ...)` overload has no `contentPadding` parameter and defaults to ~56dp height. Section headers target 48dp (matching `TabRow` / `FilterChip` touch targets). For any search field in a `topBar`:

- Use the **`TextFieldState`** overload: `OutlinedTextField(state: TextFieldState, ...)`.
- Set `lineLimits = TextFieldLineLimits.SingleLine` (replaces `singleLine = true`).
- Set `contentPadding = OutlinedTextFieldDefaults.contentPadding(top = 14.dp, bottom = 14.dp)`.
- Propagate text changes to the ViewModel via `snapshotFlow { state.text.toString() }.collect { vm.onQueryChange(it) }` inside a `LaunchedEffect(Unit)`.
- To clear programmatically: `state.edit { replace(0, length, "") }` — the `LaunchedEffect` will propagate the empty string automatically.

**Do not** use the `value/onValueChange` overload for any search field in a header row; the fixed 56dp height makes headers visually inconsistent.

---

## Cross-platform parity table

Every shipped web route maps to an Android screen unless explicitly
web-only. When you change one side, you change the other (or open a
tracked TODO with the file path).

| Concept | Web route | Android screen | Notes |
| --- | --- | --- | --- |
| Home | `/` | `screen/home/HomeTabScreen.kt` | |
| Auth — login | `/login` | `screen/login/LoginScreen.kt` | |
| Auth — register | `/register` | (web-only) | Android piggybacks login flow |
| Collections home | `/collections` | `screen/collections/CollectionsTabsScreen.kt` | Canonical index reference |
| Collection detail | `/collections/[id]` | `screen/collections/CollectionListScreen.kt` | Canonical detail reference |
| Lists home | `/lists` | `screen/collections/CollectionsTabsScreen.kt` (Lists tab) | Must match Collections home anatomy |
| List by type | `/lists/[type]` | `screen/grocery/ShoppingListScreen.kt` | |
| Item detail | (modal in collection detail) | `screen/item/ItemDetailScreen.kt` | Web edits inline; Android has dedicated screen |
| Stores | `/stores` | `screen/grocery/ShoppingStoreScreen.kt` | |
| Chores | `/collections/[id]/chores` | `screen/chores/ChoresScreen.kt` | |
| Maintenance | `/maintenance` | `screen/maintenance/MaintenanceScreen.kt` | |
| Scanner | (none — Android only) | `screen/scan/ScannerScreen.kt` | Android-only |
| Settings | `/settings` | `screen/settings/SettingsScreen.kt` | |
| About | (in `/settings`) | `screen/about/AboutScreen.kt` | |
| Bundles | `/collections/[id]/bundles` | (TODO: roadmap) | Bundles are a power-user feature; Android screen pending. Web is the primary surface. |
| Locations | `/collections/[id]/locations` | (TODO: roadmap) | Hierarchical location tree; Android screen pending. |
| Members | `/collections/[id]/members` | (TODO: roadmap) | Member management; Android screen pending. Invite flow uses deep link to login. |
| Templates | `/collections/[id]/templates` | (TODO: roadmap) | Custom field templates; Android screen pending. |
| Import | `/import` | (web-only) | Operator/admin tool |
| Profile | `/profile` | (in Settings) | |
| Invite accept | `/invite/[token]` | (deep link to login) | |
| Tasks | `/tasks` | (TODO: roadmap) | Web-first; Android screen pending. |
| Share view | `/share/[slug]` | (web-only) | Public read-only link |

Update this table whenever a route or screen is added, removed, or moved.

---

## Don'ts (regressions caught in this codebase)

Keep this list short. Each entry is a real bug we've shipped and should
never repeat.

- **Do not mix a top primary button and a dashed empty-state card on the
  same page.** (See the May 2026 `/lists` regression — a dashed "+ New
  list" card appeared below the empty state while `/collections` used a
  top-of-page button. Pages looked nothing alike.)
- **Do not hardcode list/collection types in route handlers.** Types come
  from the `UserListType` API; routes accept any slug. (See May 2026
  `lists/[type]/+page.svelte` rewrite.)
- **Do not call `$_('section.foo.${dynamic}')` with a runtime key.** If the
  key isn't in the locale files at build time, the literal key string ships
  to users. Use real fields from API responses (e.g.,
  `currentListType?.label`) instead.
- **Do not introduce new icon glyphs without registering them.** Web icons
  must pass `web/scripts/check-icons.mjs`. Android uses
  `androidx.compose.material.icons` — pick from the Material catalog, not
  ad-hoc SVGs.
- **Do not invent a new component variant inline.** If
  `Button.svelte` doesn't have what you need, add the variant to the
  component (and document it here) rather than spreading one-off styles
  across pages.

---

## When to update this document

Update **before** you write the code, in the same PR:

- Adding a new screen/route → add a row to the parity table.
- Adding a new component or component variant → add a row to the
  vocabulary table.
- Adding a new affordance pattern not currently described → add a section
  or extend the vocabulary table.
- Catching a recurring UI regression → add an entry to **Don'ts**.
- Material updates the spec in a way that affects us → update the
  Foundation section and link to the M3 release notes.

If a PR touches a `+page.svelte`, a `Screen.kt`, or a file in
`web/src/lib/components/` and does **not** touch this document, the
reviewer (or AI agent) should ask why.
