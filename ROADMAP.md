# Tangible Roadmap

This is a living plan, not a commitment. Order and scope shift as we learn.
For shipped work see [CHANGELOG.md](CHANGELOG.md). For agent rules see
[AGENTS.md](AGENTS.md).

Each phase groups changes that ship together as a coherent user story.
Within a phase, items are roughly ordered by leverage.

---

## Phase 8 — Make it shareable ✅

Today Tangible treats every user as an island. The biggest gap vs. comparable
self-hosted inventory tools is multi-user / shared collections. This phase
lands the auth + ACL plumbing once, then several user-visible features fall
out of it.

- **OIDC / OAuth2 SSO** — federate with Authelia, Authentik, Keycloak,
  Google, GitHub. Reuse the existing session machinery; add an
  `external_identity` table keyed by `(issuer, subject)`. Settings UI to
  link / unlink providers.
- **Collection ACL** — `(collection_id, user_id, role)` with roles
  `owner`, `editor`, `viewer`. Server enforces on every items / photos /
  loans / sync route. Web + Android UIs gain a "Members" panel and an
  invite-by-email-or-token flow.
- **Public read-only share links** — generate an unguessable URL for a
  collection (or a single item) that renders a stripped-down read-only
  view without auth. Per-link revoke.
- **Invitation tokens** — short-lived tokens for onboarding non-OIDC
  household members.
- **Audit log** — who changed what, when. Surface in collection settings.

---

## Phase 9 — Make items richer ✅

Once items can be shared, the next pressure is making each item carry
more useful data without manual data entry.

- **Item templates / per-type custom fields** ✅ — define reusable schemas
  ("Book", "Board game", "Tool") with default fields, units, and
  validation. Items inherit from a template; templates are
  collection-scoped and exportable.
- **URL metadata scraper** ✅ — paste an Amazon / IGDB / IMDB / Discogs
  link, prefill title, cover image, and type-specific fields. Plug-in
  adapters per source so new sites are a small contribution.
- **Document attachments** ✅ — upload PDFs (receipts, manuals, warranties)
  alongside photos. Inline preview on web; download on Android.
- **Warranty / expiry tracking** ✅ — optional "expires on" on attachments
  and items; surfaces in a dashboard widget and triggers reminders.
- **Maintenance schedules** ✅ — recurring tasks per item ("change furnace
  filter every 90 days", "service car"). Reuses the loan reminder /
  notification path. Mark-complete records history.
- **Parent / child items (containers, kits)** ✅ — a "Toolbox" item can
  contain "Hammer", "Tape measure". Move container, contents move with
  it. Exports preserve hierarchy.
- **Multi-photo upload + add photo from URL** ✅ — pick many at once on
  web/Android, or paste an image URL. Re-order; pick primary.
- **HEIC support + EXIF rotation fix** ✅ — accept HEIC server-side,
  transcode on upload, honor EXIF orientation so iPhone photos aren't
  sideways.

---

## Phase 10 — Make it efficient ✅

With more items per collection, bulk operations and discovery become the
bottleneck. This phase is about scaling the UX.

- **Bulk select + bulk actions** ✅ — web and Android now support
  multi-select with bulk set-field actions (`depleted` / `wanted`),
  bulk archive/restore, bulk delete, bulk tag add/remove,
  bulk move-to-location, and bulk lend-to-contact backed by
  collection-scoped API endpoints.
- **Better search** ✅ — global command palette search endpoint with
  accent-folding (`café` matches `cafe`) and fuzzy ranking; searches
  title/subtitle/notes/custom-fields/identifiers across all user-accessible
  collections, plus OCR/text indexing for attached documents.
- **Hierarchical / nested tags** ✅ — `electronics > audio > cables`. UI
  shows breadcrumbs; filters cascade.
- **QR code label sheets** ✅ — generate a printable PDF of QR labels for
  selected items. Android scanner gains a "find by QR" mode (vs.
  scan-to-create today) that jumps straight to item detail.
- **Wishlist / wanted items** ✅ — flag items the user doesn't own yet;
  one click converts to owned with acquisition date and price.
- **Reports** ✅ — per-collection totals (count, value), BoM PDF export,
  insurance-friendly export bundle (CSV + photos + PDFs in a zip).
- **CSV export with parent/child preserved** ✅ — round-trip the new
  item hierarchy through CSV without losing relationships.
- **Webhooks** ✅ — outbound HTTP on item events (created, updated,
  loaned, returned, maintenance-due) for Home Assistant, n8n, Discord.
- **i18n scaffold** — moved to Phase 17 where translation rollout is
  tracked as platform work.
- **Sold / disposed / donated workflow** ✅ — items can be archived
  with disposition metadata (type/date/amount/buyer/note). Explicit restore
  flow available. Buyer contact linkage via `buyer_id` FK. Audit log
  integration + disposed items report endpoint included.
- **Item flagging** ✅ — mark items for review ("verify location",
  "needs photo", "check warranty") without editing them; flag is
  cleared on next edit or explicit dismiss.
- **Relation field type** ✅ — a new template field type that points to
  another item in the same (or any) collection. Enables "sequel to",
  "accessory for", "compatible battery", "intended fuel container"
  relationships without freeform text. Renders as a linked item card.
- **Dynamic dropdown fields** ✅ — in addition to static enum lists,
  allow a select field to pull its options from existing values already
  in use for that field across the collection. Removes the "add to
  list first" friction that frustrates users of static templates.
- **Multi-value fields** ✅ — template field type that holds an ordered
  list (e.g. list of URLs, list of related ISBNs, list of actors).
  Renders as a tagged chip list; sortable; searchable.
- **Community scraper registry** ✅ — curated, version-controlled
  scraper presets are browseable/importable from the Templates tab,
  include admin trust pinning controls at API level, and documented
  contribution workflow via pull requests.

---

## Phase 11 — Become the whole-home database ✅ COMPLETE

Tangible starts as a collectibles tracker. This phase broadens it into a
complete home inventory: every room, every appliance, every tool, every
consumable. The goal is to replace the spreadsheet every homeowner
eventually makes and then stops maintaining.

**Dictionary & Scaffold Templates — ✅ COMPLETE**
- **Phase 11 kickoff** ✅ — added a new **Home Equipment** root category
  with starter leaves: Appliance, Generator, HVAC/Furnace/Air Handler,
  Water Heater, Refrigerator, Water Service Filtration, and Sump Pump.
- **Phase 11 wave 1 (ordered slices)** ✅ — completed in order:
  1) appliance-focused template defaults (server + web defaults UX),
  2) Fuel & Chemicals category set + scaffold templates aligned to
  consumable/date workflows, 3) Vehicles category set + maintenance-minded
  scaffold templates (oil/change interval, registration/insurance fields).
- **Phase 11 wave 2 (ordered slices)** ✅ — completed in order:
  1) Batteries category set + scaffold templates (rechargeable with chemistry/
  capacity/voltage, disposable with expiry, smoke detector with install tracking),
  2) Clothing & Wardrobe category set + scaffold templates (clothing items,
  footwear with size system variants, accessories), 3) Art & Décor category set
  + scaffold templates (artwork with provenance/appraisal, framed prints, 
  decorative objects with origin/era).
- **Phase 11 wave 3 (ordered slices)** ✅ — completed in order:
  1) Tools category enhancements + scaffold templates (hand tools, power tools
  with battery/service tracking, shop equipment), 2) Pantry category enhancements
  + scaffold templates (spices with bloom tracking, pantry items with minimum
  stock/storage location), 3) Sports & Recreation category set + scaffold
  templates (fitness equipment, outdoor gear with packed weight/inspection, 
  sports equipment with sport/dominant hand/restring tracking).
- **Phase 11 final (remaining vehicles)** ✅ — completed:
  Boat/PWC, Trailer, and Bicycle/E-Bike scaffold templates for the remaining
  vehicle subcategories (all 6 vehicles roots now have dedicated templates).

**Remaining Phase 11 Features**
- **Location hierarchy** ✅ — flat `item.location` text replaced with a
  self-referential `Location` tree (`home → floor → room → zone → container`,
  arbitrary depth). Server: new `location` table + `Item.location_id` FK,
  full CRUD API at `/collections/{id}/locations`, item create/update/bulk
  patch accept `location_id`, JSON backup round-trips locations by path.
  Web: dedicated `/collections/[id]/locations` tree manager, location picker
  in item create / edit / duplicate / bulk-move, location path shown in card
  + table views. Android: Room cache (`LocationEntity` + `LocationDao`,
  schema v2), location dropdown in item detail and bulk-move sheet.
- **Manual/asset bundles** ✅ — reusable manual library shipped: server
  models (`manual_bundles`, `bundle_assets`, `bundle_items`), CRUD +
  asset upload/download/primary-flag + bundle↔item linking API,
  web management page at `/collections/[id]/bundles` (create / edit /
  delete bundles, multipart asset upload by kind, mark primary, link
  and unlink items), Android viewer surfaces linked bundles on the
  item detail screen.

### New top-level category roots

**Home Equipment**
- *Appliance* — brand, model, serial number, purchase date, purchase
  price, warranty expiry, room/location, last service date, service
  interval (days). Covers washers, dryers, dishwashers, refrigerators,
  ovens, etc.
- *Generator* — fuel type (gasoline / propane / dual-fuel), tank
  capacity (gal), last run date, run interval (days, for monthly
  maintenance), last oil change date, oil type, oil capacity (qt), last
  spark plug replacement, last air filter replacement. Alerts fire when
  run interval is overdue.
- *HVAC / Furnace / Air Handler* — system type (central air, mini-split,
  boiler, heat pump), filter size, filter type (MERV rating), last
  filter change, filter change interval, last professional service date,
  refrigerant type. Alert when filter change is due. Provide sane
  default cadence presets (60 or 90 days), while keeping intervals
  fully user-editable.
- *Water Heater* — type (gas / electric / tankless / heat pump), tank
  size (gal), last anode rod replacement, last flush/drain date, target
  temp (°F/°C), warranty expiry.
- *Refrigerator* — fridge model/serial, internal water filter part
  number, last filter replacement date, replacement interval (months),
  plus optional separate feed-line/ice-maker filter tracking (part
  number, last replacement date, replacement interval), with linked
  inventory items for each replacement cartridge.
- *Water Service Filtration* — whole-home/under-sink system model,
  filter stage/type, cartridge or canister part numbers, last service
  date, replacement interval (months), and optional linked inventory
  items for replacement media.
- *Sump Pump* — last test date, test interval (days), battery backup
  type, battery last replaced.

**Fuel & Chemicals**
- *Stored Fuel* — fuel type (regular gasoline / ethanol-free /
  premium / diesel / chainsaw premix / propane / kerosene), container
  capacity (gal), quantity on hand (gal), purchase date, fuel
  stabilizer added (boolean), stabilizer brand, stabilizer added date,
  expiry / treat-by date, intended equipment (free text or FK to
  item). Depletion tracking reuses the existing `depleted` flag and
  lot model.
- *Lubricants & Fluids* — type (motor oil / gear oil / hydraulic /
  penetrating oil / WD-40 / etc.), viscosity/grade, container volume,
  quantity on hand, purchase date, expiry.
- *Chemicals & Cleaning* — product name, purpose, hazard class, SDS
  URL, purchase date, expiry date, storage location.

**Batteries**
- *Rechargeable Battery* — chemistry (NiMH / Li-ion / LiFePO4 /
  LiPo / Pb-acid), form factor (AA / AAA / C / D / 9V / 18650 /
  21700 / custom), capacity (mAh), nominal voltage (V), quantity,
  purchase date, charge cycles (integer, manually updated or inferred
  from maintenance tasks), last charge date, next charge due, assigned
  device (free text or FK to item). Maintenance task integration fires
  a "charge due" alert after a configurable idle period.
- *Disposable Battery* — chemistry (alkaline / lithium / zinc-carbon /
  silver oxide), form factor, quantity on hand, purchase date, best-by
  / expiry date, assigned devices.
- *Smoke Detector Battery Program* — supports both replaceable cells
  and detectors with sealed 10-year lithium batteries; track install
  date, replacement due date, detector location, detector manufacture
  date, and test cadence. Supports whole-home "test all detectors"
  recurring tasks.

**Vehicles**
- *Car / Truck / SUV* — year, make, model, trim, VIN, color, license
  plate, state/province, odometer (mi or km), fuel type, last oil
  change (date + mileage), oil change interval (miles), oil type,
  last tire rotation (date + mileage), tire size, tire brand, last
  alignment, registration expiry date, insurance expiry date, next
  inspection due date, next emissions test date.
- *Motorcycle / ATV / UTV* — same as above minus some fields, plus
  chain/belt last lubed, air filter last replaced.
- *Lawn & Garden Equipment* — type (riding mower / push mower /
  zero-turn / snow blower / tiller / leaf blower), engine cc/hp, fuel
  type, oil type, last oil change (date + hours), oil change interval
  (hours), last blade sharpen, last air filter, last spark plug,
  last carburetor clean, storage winterized (boolean + date).
  Integrates natively with the Fuel & Chemicals category for
  cross-referencing which fuel container is meant for each piece of
  equipment.
- *Boat / PWC* — hull ID (HIN), engine make/model/hours, last
  impeller replacement, last lower unit oil change, last winterization
  date, insurance expiry, registration expiry.
- *Trailer* — VIN, GVWR, registration expiry, last bearing repack, tire
  size, brake controller type.
- *Bicycle / E-Bike* — brand, frame size, last tune-up, last chain
  replacement, battery capacity (for e-bikes), last battery charge
  cycle check.

**Clothing & Wardrobe**
- *Clothing Item* — type (shirt / pants / jacket / dress / suit /
  shoes / etc.), brand, size (with separate size systems: US / EU /
  UK), color, material, care instructions (wash temp, dry method),
  purchase date, purchase price, condition, season (spring–summer /
  fall–winter / all-season), occasion (casual / work / formal /
  athletic), last worn date.
- *Footwear* — same schema plus sole type, width, insole last replaced.
- *Accessories* — type (watch / handbag / belt / jewelry / hat / etc.),
  brand, material, purchase date, purchase price, condition.

**Art & Décor**
- *Artwork* — type (painting / print / sculpture / photograph / mixed
  media), artist, title, medium, dimensions (H × W × D), year
  created, provenance, certificate of authenticity (boolean + doc
  attachment), estimated value, insured value, last appraisal date.
- *Framed Print / Poster* — artist, publisher, edition, print run,
  frame material, glass type (UV / standard), dimensions.
- *Decorative Object* — material, origin/country, era, estimated value.

**Sports & Recreation**
- *Fitness Equipment* — type (barbell / dumbbell / treadmill / bike /
  rower / etc.), brand, weight/spec, purchase date, last maintenance.
- *Outdoor Gear* — type (tent / sleeping bag / backpack / kayak /
  etc.), brand, packed weight, last inspection date.
- *Sports Equipment* — sport, brand, size/spec, dominant hand, last
  restring / reshaft / regrip (as applicable), purchase date.

### Enhancements to existing sparse categories

**Tools** (currently has no predefined template fields)
- *Hand Tool* — brand, model, size/spec, purchase date, purchase price,
  warranty expiry, storage location (drawer, cabinet, case).
- *Power Tool* — brand, model, serial number, voltage/amperage,
  purchase date, warranty expiry, last blade/bit change, last service,
  battery system (e.g. "DeWalt 20V MAX") for cross-referencing
  compatible batteries in the Batteries category. Include ecosystem and
  compatibility fields (brand family, voltage rail, pack size/type,
  charger model compatibility) for proprietary cordless platforms such
  as DeWalt, Ryobi, EGO, and Milwaukee.
- *Shop Equipment* — brand, model, serial number, purchase date,
  warranty expiry, last service date, service interval (months).

**Pantry** (has consumable date fields but no template fields)
- *Pantry Item* — product name, brand, category (dry goods / canned /
  frozen / refrigerated / spice / condiment / beverage), UPC/barcode,
  minimum stock quantity, current quantity, unit (each / oz / lb / g /
  ml / L), purchase date, best-by / expiry date, storage location
  (pantry shelf / freezer / fridge / cabinet).
- *Spice* — same as above, with bloom date / last toasted (optional).

### Location hierarchy

Replace the flat location text on items with a true location tree:
`Home → Floor → Room → Zone → Container`. Each node is an entity with
its own photo and QR label. Moving a container (e.g. a storage tote)
moves all of its contents.

---

## Phase 12 — Maintenance & operations hub ✅ COMPLETE

Core maintenance APIs and due-date alerts now exist. This phase expands
that foundation into a first-class operations center: scheduled care,
history, and proactive notifications across every asset.

- **Maintenance calendar** — ✅ unified alerts agenda page at `/maintenance`
  showing upcoming and overdue tasks across all collections, filtered by
  time window (7/14/30/60/90 days). Web UI complete.
- **Completion history with notes** — ✅ each mark-complete records
  odometer/hours reading, cost, technician (free text), and a note.
  History is paginated; exportable to CSV.
- **Push & email notifications** — ✅ three-channel opt-in per alert kind: Email
  digest, Browser push (Web Notifications API), and App (Android WorkManager).
  Each kind has independent on/off toggles and configurable lead time. Settings
  UI in web (**Settings → Notifications**) and Android (**Settings → Notifications**).
  Android daily alert poll: WorkManager fires once a day, fetches alerts up to
  the max lead time for push-enabled kinds, and posts a grouped local notification.
  No Firebase or APK recompilation required — works with any self-hosted server.
- **Low-stock alerts** — ✅ when a consumable item's quantity drops below
  its minimum, surface it in the alerts feed. `minimum_quantity` field
  added to Item model.
- **Maintenance consumables linkage** — ✅ associate a maintenance task
  with the consumable items it depletes. Auto-depletion on task completion.
  Track cost of materials per task.
- **Chores & recurring household tasks** — ✅ non-item-specific tasks
  (clean gutters, test smoke detectors, drain water heater sediment,
  run generator, flush water softener) with recurrence interval and
  completion log. Per-collection **Chores** tab in web UI.
- **Furnace / refrigerator / water filter workflows** — ✅ one-tap
  "Log filter change" / "Log filter service" button appears directly
  on HVAC, Refrigerator, and Water Service Filtration item cards.
  Auto-creates (or reuses) a named chore for that item and records a
  completion. Default intervals: 60 days (furnace), 180 days (fridge),
  90 days (water filter). Accessible via `POST /items/{id}/quick-chore`.
- **Generator run log shortcut** — ✅ "Ran generator today" one-tap
  action on Generator item cards. Stamps a completion on the generator's
  run-log chore and resets the 30-day overdue alert.

---

## Phase 13 — Smart home integration & discovery ✅

With rich data in place, Tangible can become a hub that other smart home
tools query and react to.

- **Home Assistant integration** ✅ — `GET /api/ha/sensors` returns per-collection sensor data (item count, low-stock count, overdue/due-soon alerts) in HA REST sensor format. `GET /api/ha/blueprint.yaml` serves a downloadable automation blueprint. Both accept Bearer token or session auth.
- **NFC tag support (Android)** ✅ — Write `tangible://item/<id>` to an NFC tag from the item detail screen. Tap any Tangible NFC tag to navigate directly to the item. QR scanner also handles `tangible://` URIs.
- **Unified physical labeling** ✅ — `GET /api/items/{id}/qr.png` serves a machine-readable PNG QR code. The bulk QR-label PDF now embeds real `tangible://item/` QR images. Both NFC and QR scans route to the same item detail screen.
- **AI-assisted item creation** ✅ — `POST /api/items/ai-prefill` accepts `{ barcode }` and queries Open Library, MusicBrainz, Open Food Facts, and Google Books; returns `{ title, subtitle, category_slug, attrs, source }` for pre-filling the add-item form.
- **Insurance export bundle** ✅ — `GET /api/collections/{id}/reports/insurance-export` already served the CSV+photos ZIP. An **Export** tab in the collection subnav now triggers it directly from the browser.
- **Field-value hyperlink filters** ✅ — Category badges, creator, condition, and location values in the collection grid and table are interactive filter buttons; clicking any value instantly narrows the item list.
- **Image gallery / "Add more images"** ✅ — Full photo gallery component with lightbox, thumbnail strip, keyboard navigation, set-as-primary, delete, and editable per-photo captions (stored in new `caption` column, migration `0031_photo_caption`).

---

## Phase 14 — Web UI redesign ✅ Wave 1-9 complete; Wave 10 A–F shipped (v0.22.0)

**Status snapshot (v0.18.16+):** All 8 waves shipped. Wave 1 (tokens +
palette), Wave 2 (component library), Wave 3 (auth/chrome), Wave 4
(secondary pages), Wave 5 (server/API), Wave 6 (collections/[id] split
into 11 child components), Wave 7 (a11y sweep + `npm run a11y`), and
Wave 8 (tabbed swipeable Collections/Lists) are all committed to main.

The web client works but feels generic and visually undifferentiated:
two hardcoded slate/sky-blue palettes, ad-hoc inline SVGs and emoji,
no shared component library, dense pages (`collections/[id]` ≈ 1,800
lines, `settings` ≈ 1,200), inline edit-in-place that swaps card
content for inputs, partial mobile responsiveness, and a few systemic
accessibility gaps. This phase rebuilds the foundation, ships a
design system, and migrates pages page-by-page so each step is
independently shippable.

**Guiding principles**
- Additive first: new components and tokens land before any existing
  page is rewritten. No page should regress while the migration runs.
- Each wave below is a **separate commit + push** that passes
  `npm run check` and `npm run build` cleanly. Mid-migration the app
  stays mixed-style; that is intentional and expected.
- Honor the [AGENTS.md](AGENTS.md) Feature Registry — every routed page
  and component listed there must keep working after each wave.

### Wave 1 — Foundations (icons, theme tokens, palette picker)

**Deliverable:** `lucide-svelte` installed; expanded design tokens in
`web/src/lib/styles.css`; 10 selectable color palettes; new
**Tangible** brand palette (indigo-violet on warm off-white / deep navy)
as the new default.

1. Add dependency in [web/package.json](web/package.json):
   `"lucide-svelte": "^0.460.0"` (or current). Run `npm install`.
2. Create `web/src/lib/Icon.svelte` — a thin one-line wrapper that
   re-exports any `lucide-svelte` icon, accepting `size`, `strokeWidth`,
   and `aria-label`. The wrapper exists so future icon-library swaps
   touch one file.
3. Rewrite [web/src/lib/styles.css](web/src/lib/styles.css):
   - **Design tokens** at the top of the file:
     - Spacing: `--space-1`..`--space-8` (4, 8, 12, 16, 24, 32, 48, 64 px).
     - Radii: `--radius-sm: 4px`, `--radius-md: 8px`, `--radius-lg: 12px`, `--radius-full: 9999px`.
     - Shadows: `--shadow-sm`, `--shadow-md`, `--shadow-lg` (subtle, theme-agnostic via rgba).
     - Type scale: `--text-xs: 0.75rem`..`--text-2xl: 1.5rem`.
     - Tap target: `--tap-min: 44px`.
   - **Color tokens** (every theme defines): `--bg`, `--surface`,
     `--surface-2`, `--border`, `--text`, `--text-muted`, `--accent`,
     `--accent-hover`, `--accent-contrast` (text on accent), `--danger`,
     `--success`, `--warning`, `--info`. Replace existing hardcoded
     hex like `#22c55e`, `#16a34a`, `rgba(0,0,0,0.45)` with these.
   - **Theme blocks** keyed by `data-theme` (light variants) and
     combined `data-theme` + `data-mode` (mode-aware tokens). The full
     palette set:

     | id | mode | bg | text | accent | accent-hover |
     |---|---|---|---|---|---|
     | `tangible-light` (default light) | light | `#FAFAF7` | `#1F1D2B` | `#7C5CFF` | `#6342F5` |
     | `tangible-dark` (default dark) | dark | `#1A1D29` | `#F0F0F5` | `#A78BFA` | `#8B6FF8` |
     | `gazette` | light | `#F2F7FF` | `#0A0A0A` | `#3B82F6` | `#2563EB` |
     | `paper` | light | `#F8F6F1` | `#4C432E` | `#AA9A73` | `#8B7B58` |
     | `cloud` | light | `#F1F2F0` | `#35342F` | `#37BBE4` | `#1D9BC4` |
     | `passion` | light | `#F5F5F5` | `#12005E` | `#8E24AA` | `#6A1B89` |
     | `tron` | dark | `#242B33` | `#EFFBFF` | `#6EE2FF` | `#41C9EB` |
     | `espresso` | dark | `#21211F` | `#D1B59A` | `#9C7B5A` | `#7A5C40` |
     | `onedark` | dark | `#282C34` | `#DFD9D6` | `#98C379` | `#7DA85F` |
     | `blues` | dark | `#2B2C56` | `#EFF1FC` | `#6677EB` | `#4D5DD9` |
     | `blackboard` | dark | `#1A1A1A` | `#FFFDEA` | `#FFB347` | `#E8923A` |

     Pick `--surface`, `--surface-2`, `--border`, `--text-muted`,
     `--accent-contrast`, `--danger/success/warning/info` for each
     theme by adjusting `bg`/`text` ±5–10% in HSL. Use
     `color-mix(in srgb, ...)` where helpful. Every theme must pass
     **WCAG AA** for body text (verify with `npx pa11y` or manual
     contrast check).
4. Refactor [web/src/lib/theme.ts](web/src/lib/theme.ts):
   - Persist **two** keys in localStorage: `tangible:theme-mode`
     (`light | dark | system`, existing) and `tangible:theme-palette`
     (id from the table above, default `tangible`).
   - Compute the resolved `data-theme` as `${palette}-${mode}` for
     palettes that define both (currently only `tangible`); for
     single-mode palettes (e.g. `paper` is light-only), apply that id
     directly and lock the mode toggle for that palette.
   - Expose `palette` writable store and `availablePalettes` constant
     `[ {id, name, mode, bg, accent}, ... ]` driven from a single
     source of truth in `theme.ts`.
   - Remove the hardcoded `META_COLOR` map; read the resolved theme's
     `--bg` at runtime via `getComputedStyle(document.documentElement)`
     and update `<meta name="theme-color">` accordingly.
5. Update the pre-hydration script in
   [web/src/app.html](web/src/app.html):
   - Read both keys; resolve to a `data-theme` attribute the same way
     `theme.ts` does.
   - Fall back to `tangible-dark` if anything fails.
6. Update **Settings → Appearance**
   ([web/src/routes/settings/+page.svelte](web/src/routes/settings/+page.svelte)):
   - Keep the existing `light / dark / system` toggle.
   - Add a palette grid below: each card shows the palette name plus a
     2-swatch preview (background + accent disc). Click selects the
     palette. Selected palette has an outlined ring.
   - Group palettes by mode (Light / Dark) with section headings.
   - Persist selection via the `palette` store.

**Acceptance:** running `npm run dev`, every existing page renders in
the new default `tangible` palette without regressions; switching
palettes updates the entire app live; reload preserves the choice;
no FOUC; `npm run check` and `npm run build` are clean.

### Wave 2 — Shared component library

**Deliverable:** `web/src/lib/components/` directory with the
components below. None of the existing pages are migrated yet — these
are added alongside.

Build in this order (each subsequent component can use the earlier ones):

1. `Icon.svelte` (already in Wave 1).
2. **`Button.svelte`** — props: `variant: 'primary' | 'secondary' | 'danger' | 'ghost'`,
   `size: 'sm' | 'md' | 'lg'`, `loading: boolean`, `disabled: boolean`,
   `icon?: string` (lucide name) and `iconPosition: 'left' | 'right'`.
   Always honors `--tap-min` for `md`/`lg`. Uses an inline spinner SVG
   when `loading=true`.
3. **`IconButton.svelte`** — square variant of Button. Requires
   `aria-label` (TypeScript prop typed as required).
4. **`Badge.svelte`** — `variant: 'neutral' | 'success' | 'warning' | 'danger' | 'accent' | 'info'`,
   `size: 'sm' | 'md'`, optional leading icon. Used for status pills
   and counts.
5. **`Alert.svelte`** — `variant: 'info' | 'success' | 'warning' | 'danger'`,
   optional `title`, dismissable, has `role="alert"` and
   `aria-live="polite"`. Renders an icon by variant.
6. **`FormField.svelte`** — wraps label + input slot + hint + error
   slot. Auto-binds `for`/`id` and `aria-describedby` to slotted
   input. Marks required fields with a red asterisk + `aria-required`.
7. **`Modal.svelte`** — backdrop + centered panel, `aria-modal="true"`,
   focus trap (use `focus-trap` or hand-rolled), Escape closes,
   backdrop click closes (configurable), `aria-labelledby` from
   `title` prop. Body slot scrolls with `max-height: 85vh`.
8. **`ConfirmDialog.svelte`** — wraps `Modal` for destructive
   confirmations. Props: `open`, `title`, `message`, `confirmLabel`,
   `confirmVariant: 'danger' | 'primary'`, `onConfirm`, `onCancel`.
   Replaces every `confirm()` native call in the codebase.
9. **`EmptyState.svelte`** — icon + headline + body + CTA slot.
10. **`SectionCard.svelte`** — `.card` replacement: header (icon +
    title + actions slot) + body slot.
11. **`Tabs.svelte`** — `role="tablist"` with arrow-key keyboard nav
    and `role="tabpanel"` for slotted content. Accepts an array of
    `{ id, label, icon? }`.
12. **`DataTable.svelte`** — generic table:
    - Props: `columns: Array<{key, label, sortable?, render?}>`,
      `rows: any[]`, `getRowId`, optional `actions` slot per row,
      optional `bulkActions` slot when selectable.
    - Built-in sort (click column header), optional client-side filter
      input slot.
    - **Mobile fallback at `max-width: 640px`**: each row renders as a
      stacked card (label + value pairs). The component owns this — no
      consumer changes required.
    - Sticky header on long tables.
13. **`Toast.svelte`** (upgrade existing) — add optional `action`
    slot, dismiss button, configurable duration, queue support.

For each component, write a minimal usage example as a
`<!-- USAGE: ... -->` comment block at top so future contributors can
copy/paste.

**Acceptance:** importing each component from `$lib/components/` works
in a scratch route; `npm run check` clean; no existing page changed.

### Wave 3 — Migrate auth, profile, and shared chrome

Lowest-risk pages. Apply new components and lucide icons.

- [web/src/routes/+layout.svelte](web/src/routes/+layout.svelte) —
  replace inline SVGs (sparkles, hamburger, chevron, bell pictogram)
  with `<Icon name="...">`. Replace `.icon-btn` with `IconButton`.
  No structural change.
- [web/src/routes/login/+page.svelte](web/src/routes/login/+page.svelte) —
  add `user` and `lock` icons inside inputs (left padding +
  absolutely-positioned `<Icon>`); password show/hide eye button;
  loading spinner on submit (via `<Button loading>`); wrap errors in
  `<Alert variant="danger">`; OIDC providers as styled `<a class="oidc-pill">`
  with provider name.
- [web/src/routes/register/+page.svelte](web/src/routes/register/+page.svelte) —
  same input-icon pattern; persistent password requirement hint
  ("At least 12 characters") via `FormField` hint slot; loading
  spinner; wrap form fields in `FormField`.
- [web/src/routes/profile/+page.svelte](web/src/routes/profile/+page.svelte) —
  switch username `disabled` → `readonly`; `FormField` everywhere;
  `<Alert>` for success/error; password strength meter component
  (simple inline: bar with `weak / fair / strong` based on length +
  variety).
- [web/src/routes/invite/[token]/+page.svelte](web/src/routes/invite) —
  `EmptyState` for error; show inviter and expiration if API exposes;
  `<Button>` for accept.
- [web/src/routes/share/[slug]/+page.svelte](web/src/routes/share) —
  `SectionCard` wrapper; humanize category slugs via existing
  `categories.ts` helper; show item count + "Shared collection" badge;
  no copy-link button (out of scope).
- [web/src/lib/Toast.svelte](web/src/lib/Toast.svelte) — replace
  unicode `✓ ✕ ⚠ ℹ` with `<Icon name="check|x|alert-triangle|info">`.
- [web/src/lib/AlertsDropdown.svelte](web/src/lib/AlertsDropdown.svelte) —
  per-kind icon next to alert title (use a small mapping
  `{maintenance_due: 'wrench', chore_due: 'sparkles', item_use_by: 'clock', low_stock: 'package-x'}`);
  "View all alerts" footer link to `/maintenance`; severity icon
  (`alert-circle` red / `alert-triangle` yellow) instead of dot.
- [web/src/lib/WhatsNew.svelte](web/src/lib/WhatsNew.svelte) — sticky
  modal header; close button uses `<Icon name="x">`.

**Acceptance:** all the above pages render, function, and pass
`npm run check`. Walk through each page in dev to verify no regression.

### Wave 4 — Migrate secondary pages

Same pattern (components + icons + small UX fixes) for the lower-risk
collection sub-pages.

- **`maintenance/+page.svelte`** — group sort by urgency (overdue
  first); per-kind alert icon; left-border color by severity
  (`--danger` / `--warning`); celebratory `EmptyState` ("All caught
  up!") with `party-popper` icon when no alerts in range.
- **`collections/[id]/locations/+page.svelte`** — replace
  `\u00a0\u00a0`-padding for tree depth with CSS `padding-left`
  proportional to depth; per-kind icon (`home`, `building`, `door-open`,
  `map-pin`, `package` for home/floor/room/zone/container); proper
  `<ul role="tree">` semantics; `ConfirmDialog` for delete.
- **`collections/[id]/chores/+page.svelte`** — bigger overdue
  indicator (left-border + `alert-circle` icon); "Snooze 1 day"
  quick-action button; `ConfirmDialog` for delete; `Modal` for "Mark
  done" form.
- **`collections/[id]/bundles/+page.svelte`** — replace `confirm()`
  with `ConfirmDialog`; per-asset-kind icons (`book-open` manual,
  `image` diagram, `file-cog` firmware, `wrench` service, `nut` parts,
  `file` other); group `<select>` options with `<optgroup>`; `Modal`
  for upload.
- **`collections/[id]/templates/+page.svelte`** — convert 7-column
  field-builder table into a card-per-field layout (one `SectionCard`
  per field, fields ordered top-to-bottom with up/down reorder
  buttons); JSON view becomes a `<details>` collapsible at the bottom
  for power users; type-dependent fields (source, options) only
  render when relevant type is selected.
- **`collections/[id]/members/+page.svelte`** — copy-to-clipboard
  button beside the one-time invite URL (`<IconButton icon="copy">`
  with toast feedback); humanize audit log entries (replace raw
  action codes + UUIDs with rendered sentences using existing actor
  + target lookup); `ConfirmDialog` for member removal; collapsible
  sections (members, invitations, share links, audit) with default
  state members=open, others=closed.
- **`lists/[type]/+page.svelte`** — replace 🏪 emoji with
  `<Button icon="store">Manage stores</Button>`; convert two-row add
  form into single primary row + `<details>` "More options"; use
  `DataTable` (which gives mobile card fallback for free); per
  list-type icon in header (`shopping-cart` groceries, `wrench`
  hardware, `house` home_goods, `star` wish_list).
- **`import/+page.svelte`** — replace mode `<select>` with 4 radio
  cards (icon + name + 1-line description: `file-archive` CLZ,
  `file-spreadsheet` CSV, `list` List, `database-backup` Restore);
  CSV mapping textarea inside `<details>` with a worked example shown
  above; result rendered as `<Alert variant="success|danger">` with
  a `<details>` containing the raw JSON body.
- **`lib/ItemComments.svelte`** — `ConfirmDialog` for delete;
  `<time datetime="ISO">` wrapping every timestamp; reply button uses
  `corner-down-right` icon.
- **`lib/PhotoGallery.svelte`** — convert thumbnail `<div>`s with
  `onclick` into `<button>`s; lightbox prev/next icons via
  `<Icon name="chevron-left|chevron-right|x">`; reposition lightbox
  nav inside image bounds at `max-width: 640px`; arrow-key
  navigation between photos.
- **`lib/ShoppingStoreManager.svelte`** — stack the two-panel layout
  vertically below `768px` (left panel becomes a top tab strip,
  right becomes the panel below); aria-labels on ↑/↓ buttons.

**Acceptance:** each page passes `npm run check` after edit; walk
through manually in dev to confirm no behavior regression. Commit
each page individually so reverting one is easy.

### Wave 5 — Restructure `settings`

The existing `settings/+page.svelte` (~1,200 lines) becomes 5 routes
under `web/src/routes/settings/`:

- `/settings` (index) — Appearance (theme mode + palette grid from
  Wave 1) + Account (export, delete).
- `/settings/notifications` — the per-kind notification preference
  table; convert to one `SectionCard` per kind with a toggle switch
  and a "Lead time" number input + label.
- `/settings/security` — TOTP setup / disable / regen-backup-codes.
  Add copy buttons on QR-secret and each backup code; "Download
  codes as .txt" button.
- `/settings/tokens` — API token list + create form. Create flow
  shows the new token in an `<Alert variant="warning">` with
  copy-to-clipboard and a one-line "This is shown only once" notice.
- `/settings/admin` (gated by `me.is_admin`) — server settings + barcode
  adapters + system maintenance. Add a search input above the
  settings grid that filters rows by key/label/description. Group
  settings into collapsible sections by category (already grouped in
  the API response — render each group as a `SectionCard` collapsible
  with first 3 expanded by default).

A shared `web/src/routes/settings/+layout.svelte` renders a left
sidebar with `Tabs`-style nav (or top tabs on mobile) so users can
switch between sections. The "/settings?enroll=1" deep link from the
layout (used to force TOTP enrollment) redirects to
`/settings/security?enroll=1` instead.

**Acceptance:** every prior `/settings` capability is reachable from
the new routes; no admin or user setting is dropped (cross-check the
existing file before deleting it); URLs like `/settings`,
`/settings/security`, `/settings/admin` all render; `npm run check`
and `npm run build` clean.

### Wave 6 — Restructure `collections/[id]/+page.svelte`

The biggest single page (~1,800 lines). Strategy: keep the
`+page.svelte` route but split into colocated child components:

```
web/src/routes/collections/[id]/
  +page.svelte                  (orchestration + state + data fetching)
  AddItemCard.svelte            (the create form, top of page)
  FilterBar.svelte              (search + view toggle + sort)
  AdvancedFilters.svelte        (root cat + tags + status filters; collapsed by default)
  BulkToolbar.svelte            (sticky when items selected)
  ItemGrid.svelte               (card view)
  ItemTable.svelte              (uses DataTable)
  ItemEditPanel.svelte          (slide-over panel; replaces inline edit)
  modals/DeleteItemDialog.svelte
  modals/MarkOwnedDialog.svelte
  modals/ArchiveItemDialog.svelte
  modals/FlagItemDialog.svelte
```

Each child is a Svelte 5 component receiving props and emitting
events back to `+page.svelte`. Shared item-mutation logic stays in
`+page.svelte` (or a new `web/src/routes/collections/[id]/state.ts`
module).

**Specific UX changes (must all land in this wave):**

- **Inline edit-in-place is gone.** Clicking edit on an item opens
  `ItemEditPanel.svelte` as a right-side slide-over (full-height,
  `max-width: 480px`, with backdrop). On mobile (`<640px`) the panel
  becomes a full-screen overlay. Save/Cancel in a sticky footer.
- **Filter bar** (always visible): search input + view toggle
  (grid/table) + primary sort.
- **Advanced filters** (`<details>` collapsed by default on mobile,
  open on desktop ≥1024px): root category + status filters
  (depleted/wanted/archived) + tag chips + tag-mode toggle + custom
  sort attribute.
- **Bulk toolbar**: sticky to the top of the items area only when
  ≥1 item selected. Counter + Select-visible / Clear / a single
  `<DropdownMenu>` containing all bulk actions grouped by category
  (Status, Organize, Manage). Replaces the current ~15-button row.
- **Row actions**: in both grid and table, secondary actions
  collapse into a `<IconButton icon="more-horizontal">` opening a
  small popover menu. Primary actions (edit, photos) stay visible.
- **Status badges**: collapse the multi-badge row into one `<Badge>`
  per non-default state with an icon (`flag` flagged, `circle` wanted,
  `archive` archived, `x-circle` depleted) plus tooltip on hover.
- **Consumable date editing** moves into `ItemEditPanel` (it currently
  uses a `colspan="100"` table row hack).
- Replace native `confirm()` and ad-hoc delete prompts with
  `ConfirmDialog`.

**Regression check (per [AGENTS.md](AGENTS.md)):** before and after,
walk the Feature Registry rows that touch this file:
*Items CRUD + filtering*, *Tag filter chips (AND/OR)*,
*Field-suggestions type-ahead*, *Item custom sort order*,
*Photo drag-to-reorder*, *Item comment threads*. Each must still work.
Write a short manual checklist into the commit body.

**Acceptance:** all six Feature Registry rows above still work;
`npm run check` and `npm run build` clean; manual smoke through
filter/sort/edit/delete/bulk on a dev DB; mobile layout verified at
375px, 768px, 1024px viewport widths.

### Wave 7 — Mobile polish + accessibility sweep

Final pass across the whole app:

- Audit every `<button>` and clickable element for `--tap-min`. Apply
  `min-height: var(--tap-min)` on small buttons that fail.
- For each page, test at 375px, 414px, 768px, 1024px in Chrome
  devtools. Fix breakages (overflow, wrapping, off-screen modals).
- Add `axe-core` to the dev dependencies and a `npm run a11y` script
  that runs `pa11y-ci` against `npm run preview`. Fix any new
  violations introduced; document remaining ones as known issues.
- `<time datetime="ISO">` everywhere a date/time is rendered.
- Verify focus trap correctness on every Modal usage (inspect via
  keyboard tab navigation).
- Update [docs/user-guide.md](docs/user-guide.md) with new theme
  picker and any UX changes that affect documented workflows.
- Update [CHANGELOG.md](CHANGELOG.md) under the active version with
  user-facing entries (themes, redesign, etc.). Per AGENTS.md, the
  CHANGELOG drives the in-app "What's new" modal.
- Bump `web/package.json` minor version when the work ships under a
  numbered release.

**Acceptance:** `npm run check`, `npm run build`, `npm run a11y` all
clean; no obvious mobile breakage at the four viewport widths; user
guide and changelog updated.

### Wave 8 — Web/Android continuity for Collections and Lists

The Android shell uses tabbed swipeable views for both Collections
(`CollectionsTabsScreen`) and Lists (`ShoppingListScreen` with the
inner store/aisle pager); the web client today still renders one
collection or one shopping list at a time. Bring the two shells into
visual and gestural parity so a touchscreen laptop user feels at
home in either client.

- **`/collections`** — replace the current grid of cards with a
  tabbed view: a top tab strip lists every collection (plus a leading
  "All" tab that keeps the existing grid). Tabs are
  horizontally-scrollable when they overflow. Tab content is the
  existing `/collections/[id]` page (after Wave 6 split, render the
  child components inline). Swipe-left / swipe-right and trackpad
  pan navigates between tabs (use the new `Tabs.svelte` plus an
  `embla-carousel-svelte` or a hand-rolled `pointerdown` /
  `pointermove` swipe handler — keep the dependency footprint small).
  Persist last-viewed tab in `localStorage`.
- **`/lists`** — same treatment for the four shopping list types
  (Groceries, Hardware, Home Goods, Wish List). The `/lists` landing
  remains as a fallback grid for browsers without JS, but on hydrate
  it converts to the tabbed view. Per-list inner content (the current
  `/lists/[type]` page) renders inside each tab.
- **Animation / accessibility** — respect
  `prefers-reduced-motion: reduce` (snap instead of animate). Keyboard
  navigation: arrow keys move the focus tab and the visible panel, as
  defined in the WAI-ARIA tabs pattern.
- **Routing** — keep the `/collections/{id}` and `/lists/{type}`
  URLs as deep links: opening one of those URLs jumps to the matching
  tab on hydrate. Deep-linking remains the canonical share URL.

**Acceptance:** opening `/collections` and `/lists` on a touchscreen
laptop feels like the Android client (single screen, tabs across the
top, swipe-to-switch); existing deep-links still work; `npm run check`
and `npm run build` clean.

### Wave 9 — Polish, bug fixes, and unified design language

Post-Wave-8 follow-up. Addresses visual bugs surfaced during QA and
establishes a cross-platform design language shared between the web
client and Android app.

**Bug fixes (must ship before any release tag):**

- **Tab state race condition** — `collections/[id]/+page.svelte` calls
  `load()` when `cid` changes, but the async function reads `cid`
  (a reactive `$derived`) at each `await` boundary. If the user switches
  tabs before the previous fetch completes, subsequent awaits read the
  NEW cid while the fetch-in-flight still has the old one. Fix:
  snapshot `cid` at the start of `load()` and use the snapshot
  throughout; add a generation counter so stale responses are discarded.
  Also reset `didSeedDefaults` and all filter state on each tab switch
  so they don't carry over.
- **Horizontal overflow / whitespace scroll** — item card and table row
  text elements need `min-width: 0` + `overflow: hidden; text-overflow:
  ellipsis; white-space: nowrap` on text cells so long titles don't
  push the row wider than the viewport on small screens.
- **Category-aware secondary text** — the second line on item cards and
  table rows should adapt to collection type:
  - Music: `artist` (from `attrs.creator`)
  - Books: `author` (from `attrs.creator`)
  - Movies/TV: `director` + `subtitle`
  - Groceries / Home Goods / Hardware: `brand` (from `attrs.brand` or
    `attrs.creator`)
  - Default: `subtitle` if present, else blank
  Implement a helper `secondaryLine(item, categorySlug)` in
  `web/src/lib/itemDisplay.ts` and use it in both `ItemGrid` and
  `ItemTable`.
- **Dark-mode logo shield contrast** — the shield SVG in the title bar
  uses a fill that blends into the `granite` dark background. Fix by
  either: (a) adding a white/light border or drop-shadow to the shield
  element in `static/branding/`, or (b) using `currentColor` so the
  shield inherits the header text color. Must be visible at 4.5:1
  contrast against both granite-dark and tangible-dark backgrounds.

**UX parity: Collections and Lists pages:**

- Both the `/collections` tab strip and the `/lists/[type]` tab strip
  use the same CSS classes and keyboard/swipe behavior (already done
  in Wave 8). Remaining gap: the filter and action controls on each
  page are at different vertical positions and have inconsistent
  affordances (dropdowns vs. buttons vs. links). Normalize to a shared
  `<Toolbar>` pattern: one sticky row with search on the left, primary
  action (add item / add list entry) on the right. Secondary filters
  collapse into a `<details>` row below the toolbar, closed by default
  on mobile, open on desktop >=1024px.
- Reduce vertical scroll: the "Add item" card currently sits above
  the filter bar. Move it to an inline `+` button in the toolbar, which
  opens a compact slide-in form. The filter bar and item list then start
  near the top of the viewport with no full-card offset.
- The Lists `[type]` pages should match this toolbar layout (add
  entry as a one-liner, filters in a collapsible row).

**Cross-platform design language (web + Android):**

Inspired by the Unity UI Design System (systematic spacing, a limited
type scale, and a small set of reusable surface/overlay patterns). The
goal is NOT a full Figma-style component library, but a set of shared
constraints that make the two clients feel like the same product:

- **Spacing scale**: `4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px` (already
  in `--space-1..8`). Android uses dp equivalents; verify
  `android/app/src/main/java/io/github/bradbrownjr/tangible/ui/theme/`
  spacing tokens match.
- **Type scale**: `xs=12 / sm=14 / base=16 / lg=18 / xl=20 / 2xl=24`.
  Android Material 3 equivalents: `labelSmall / bodyMedium / bodyLarge /
  titleMedium / titleLarge / headlineMedium`.
- **Surface layers**: 3 levels (`bg / surface / surface-2`). Both
  clients use the same layer for the same purpose: bg=page, surface=card,
  surface-2=elevated/hover.
- **Accent palette parity**: both the granite (web default) and tangible
  palettes define `--accent` in CSS; Android's `MaterialTheme.colorScheme
  .primary` should resolve to the same hex. Hard-code `#22A88E` (granite
  teal) as the primary in `Color.kt` for the granite equivalent, and
  `#A78BFA` for the tangible/violet palette.
- **Card anatomy**: every list item in both clients uses the same
  anatomy: (leading icon or thumbnail) + (primary text) + (secondary
  text) + (trailing actions). Ensure `ItemGrid` and `ItemTable` in web
  and `CollectionItemCard` in Android follow this pattern.
- **Interaction states**: hover/focus ring on web = 2px `accent` offset-2
  outline; Android ripple uses `primary` at 12% opacity. Both use the
  same `--radius-md` = 8dp/px for card corners.

Document the shared tokens in `AGENTS.md` under a new
"Design Language Tokens" section so Android contributors can keep them
in sync.

### Wave 10 — Unified UI patterns and discoverability

Wave 9 closed the visual gaps (themes, dark mode, filter layout). Wave
10 closes the remaining **interaction-language** gaps surfaced in
end-user QA on v0.21.x: the Add-item card, the items table, sub-page
navigation, and the Templates page all behave differently depending on
where you are in the app. This wave unifies them around a single set
of patterns and reduces vertical/horizontal scroll on the busiest
pages.

**Guiding rules for this wave**

- One Add pattern, one Filter pattern, one Items-table pattern,
  reused everywhere.
- Implicit context wherever possible — a control that asks "which
  collection?" must not appear on a page that already _is_ a
  collection.
- Lists/Collections sub-functions open in **modals**, not by pushing
  the items list further down the page.
- Tabs name the page; the page does not also h1 its own name.
- `lucide-svelte` (via `$lib/Icon.svelte`) is the only icon source.

The wave ships in lettered sub-tasks A through H. Each is an
independently shippable commit that passes
`cd web && npm run check && npm run build` cleanly.

#### A. Unified Add-item card

The collection-detail Add card and the Lists Add card currently
diverge: collections show a permanent two-row form (category + sub
+ query + Scan + Add) with no progressive disclosure; Lists show a
compact one-row form with a `+ More options` `<details>` for the rest.
Adopt the Lists pattern everywhere.

- Rewrite [web/src/routes/collections/[id]/AddItemCard.svelte](web/src/routes/collections/[id]/AddItemCard.svelte) to one primary
  row: category root + leaf + URL/ISBN/EAN/title input + **Scan image**
  + Add. Everything else (creator, subtitle, custom slug, etc.) moves
  into a `<details class="more-options">+ More options</details>`
  collapsed by default.
- Lists Add card already has `+ More options` — port the **Scan image**
  affordance to it for parity (currently only on collections). Image
  scan in Lists context resolves the barcode through the existing
  metadata adapters and prefills `name` / `brand` / `category_slug`.
- Implicit-context rule: when rendered inside `/collections/[id]`, the
  collection picker is not present (the addition implicitly targets the
  current collection). When the same component is rendered on a future
  global "quick add" widget on `/` (home), the collection picker IS
  shown — pass it as an opt-in prop `showCollectionPicker={true}`,
  default `false`. Same rule for Lists: on `/lists/[type]` the list
  type is implicit; the picker is hidden.
- Default category selection on collection-detail uses the
  collection's `default_category_slug` (already shipped in Wave 6) —
  not a hardcoded "Other / Generic". On Lists, default category =
  "(none)" so the user can opt into a category, not opt out.
- Default backing-collection logic on Lists already prefers
  Pantry / Hardware / Home Goods by name; keep that. Do not change.

**Acceptance:** the Add card looks and behaves identically across
`/collections/[id]` and `/lists/[type]`; on a collection page no
collection picker is shown; the **Scan image** button works on both.

#### B. Lists items table — column layout + DataTable

The Lists items list is currently a stacked block per row (brand
above, title bold, then collection name, badges, qty, actions all
wrapping). On any viewport ≥ 640px this should be a true table
matching the collection items table.

- Replace the bespoke `<ul>` rendering in
  [web/src/routes/lists/[type]/+page.svelte](web/src/routes/lists/[type]/+page.svelte) with the shared
  `$lib/components/DataTable.svelte` (built in Wave 2 with built-in
  mobile card fallback).
- Columns: **Brand** (small muted, optional) · **Item** (bold +
  optional subtitle below) · **Category** (chip) · **Qty** · **Notes**
  (truncated) · trailing **actions** slot (mark purchased / edit /
  delete).
- Brand column is currently dropped from the visible row — re-add it
  as a small muted column at far left, max-width ~10ch with ellipsis.
- Eliminate horizontal scroll: each text cell uses `min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap`.
  Title cell is the flex-grow column. The mobile fallback (DataTable
  built-in at `max-width: 640px`) renders each row as a stacked card
  with label/value pairs, so phones still get the dense view.
- Wish list keeps its priority chip and external link affordance —
  add them as additional columns / actions when `listType ===
  'wish_list'`.

**Acceptance:** no horizontal scroll on `/lists/groceries` at viewports
≥ 768px; the four list types render in a consistent table; mobile
cards still show all the same information.

#### C. Unified search/filter pattern

Today: collection-detail has a permanently-visible search row plus a
collapsed `<details>` for advanced filters; Lists has none. Move both
to a single shared pattern.

- Combine search input + sort + sort-direction + advanced filters into
  one collapsible **Filters** section. On viewports ≥ 1024px it is
  open by default; on smaller it is collapsed.
- One row visible in the collapsed state: a small **Filters** chip
  (with active-count badge, e.g. "Filters · 2") + the **+ Add** action
  on the right, both flush to the toolbar above the items table.
- When expanded, the Filters block contains: Search input, Sort
  selector, Direction toggle, plus the existing Category / Ownership /
  Archived / Tag-chip controls. All sit inside the same SectionCard.
- Lists pages get the same Filters block (search, sort by name / qty /
  date added / category, filter by category, filter by purchased
  state). Today they have none.
- The shared Filters block is its own component:
  `web/src/lib/components/FiltersPanel.svelte`. Both
  `routes/collections/[id]/FilterBar.svelte` and
  `routes/lists/[type]/+page.svelte` consume it.

**Acceptance:** identical Filters affordance on both pages; the active
filter count is visible in the collapsed-state chip; URL query params
keep working as deep links.

#### D. Drop redundant page titles

When a route's identity is already shown by an active tab, the
duplicated h1 is noise.

- `/collections/[id]` — remove the `<h1>{collection.name}</h1>`. The
  Collections tab strip (Wave 8) already shows the active collection.
- `/lists/[type]` — remove the `<h1>{typeTitle(listType)}</h1>`. The
  Lists tab strip already shows the active list.
- Keep page titles on standalone routes that have no tab strip:
  `/maintenance`, `/import`, `/settings/*`, `/login`, `/register`.
- Update `<svelte:head><title>` so the browser tab still shows
  "Tangible · Pantry" etc. — that does not duplicate on screen.

**Acceptance:** no visible duplicated heading; document title in the
browser still reflects the active route.

#### E. Stores promoted to top-level nav

The "Manage stores" button on Lists pages becomes a primary nav
destination so it is discoverable from anywhere.

- Add **Stores** to the main nav between **Lists** and **Maintenance**
  (icon: `lucide:store`).
- New route `web/src/routes/stores/+page.svelte` that renders the
  existing `$lib/ShoppingStoreManager.svelte` content as a full page
  (no modal wrapper).
- Remove the **Manage stores** button from the Lists header.
- "Stores" is a single shared list across all four list types — no
  per-list scoping.

**Acceptance:** clicking **Stores** in the nav shows the full store
manager; the Lists header no longer has the inline Manage-stores
button; existing per-store data is unchanged.

#### F. Collection sub-tabs → icon toolbar with modals

Layered tabs (top: Collection tabs, then sub-tabs: Items / Templates
/ Locations / Bundles / Chores / Members / Import / Export) are
disorienting. Replace the inner row with an **icon toolbar** of
single-purpose buttons, each opening a **modal** instead of pushing
the items list down the page.

- Convert the inner sub-nav in
  [web/src/routes/collections/[id]/+layout.svelte](web/src/routes/collections/[id]/+layout.svelte) from a
  Tabs component into a horizontal `Toolbar` of `IconButton`s:
  - `lucide:file-cog` Templates
  - `lucide:map-pin` Locations
  - `lucide:box` Bundles
  - `lucide:wrench` Chores
  - `lucide:users` Members
  - `lucide:upload` Import
  - `lucide:download` Export
  Each button has a `tooltip` and accessible `aria-label`. The
  **Items** view is the always-visible page body — no toolbar button
  for it.
- Each icon opens a `<Modal>` that renders the matching sub-page's
  content. **Deep links to sub-pages are not a requirement** — the
  existing `/collections/[id]/{templates,locations,bundles,chores,members,import,export}`
  routes are removed in favor of modals, with a redirect from each
  old URL to `/collections/[id]` (the toolbar makes the function
  reachable in one click). This simplifies the implementation: each
  sub-page becomes a single `<sub>Panel.svelte` mounted directly in
  the modal, no shared full-page wrapper needed.
- Modal closes return focus to the originating toolbar button. Modal
  size adapts to content (Locations and Templates need wide; Members
  is medium; Import/Export are small).
- The active toolbar button (when its modal is open) shows the
  accent color so users know what they are looking at.
- Mobile (<640px): the icon toolbar wraps to two rows; modals become
  full-screen sheets via the existing `Modal` component's mobile
  fallback.

**Acceptance:** the inner Items/Templates/... tab strip is replaced
by an icon toolbar; clicking each icon opens a modal containing the
sub-page; deep links like `/collections/[id]/templates` still render
the same content as a full page; no Items list shifts down to make
room for sub-page content.

#### G. Templates page rewrite — clarify scrapers vs custom fields

Today the Templates page mixes two concepts in one stack: a
**Community scraper registry** (Open Library / MusicBrainz / Open
Food Facts presets) and **Custom fields** (the actual template
definition). Users do not understand the relationship.

The fix is a clearer mental model + UI:

- **Templates = additional fields** that augment the collection's
  default category template. For a Music collection, a template might
  add `Pressing year`, `Catalog #`, `Label`. Items in this collection
  inherit the template's fields in addition to the built-in fields
  for the chosen category.
- **Scrapers** are a separate concern: they autopopulate the built-in
  fields and any matching template fields when you scan or paste a
  URL/ISBN/EAN. Scrapers are configured per-server and do not need
  to live on every collection's Templates page.

UI changes:

- Move the Community scraper registry **out** of the Templates page
  and into a new modal opened from the **+ Add field** flow:
  "Start from a scraper preset" link. The modal lists the scrapers
  with a one-line description; selecting one creates a template
  pre-populated with that scraper's expected fields and links the
  template to the scraper for auto-population on item add.
- Rewrite the Templates page intro:
  > "Templates add custom fields (e.g. **Pressing year**, **Catalog #**)
  > to items in this collection. Each template extends the built-in
  > fields for its category. Items inherit the matching template
  > automatically based on their category."
- Replace "No custom fields yet." / "+ Add field" / "Create template"
  with a clearer two-step wizard:
  1. **+ New template** opens a modal: "What kind of items?"
     (category picker, defaults to the collection's
     `default_category_slug`).
  2. After category, fields editor opens: "Add a field" rows with
     Name / Type / Required / (type-specific options).
  At any point: "Start from a scraper preset" pulls the scraper modal
  from above.
- Keep the **Advanced (JSON)** affordance for power users — a
  collapsible at the bottom shows the full JSON definition.

Server changes (decide during implementation):

- Inspect `ItemTemplate` to see whether it already references a
  scraper. If yes, surface the link in `GET /collections/{id}/templates`
  so the UI can show "Linked to: Open Library" beside the template
  name. If no, add a nullable `scraper_id` text column via an Alembic
  migration. Pick whichever is logical given the existing model — do
  not over-engineer.

**Acceptance:** the Templates page reads as one concept (custom
fields), with scrapers reachable as an opt-in starting point; the
two-step "+ New template" wizard works end-to-end; an item added
via Scan image in a collection that has a scraper-linked template
gets its template fields auto-populated.

#### H. Icon source enforcement

A grep across `web/src` for inline `<svg>` and emoji used as iconography
should return only `$lib/Icon.svelte`'s internal usage and palette
swatches.

- Sweep all child components added in Waves 6–9 for stray `<svg>` and
  emoji icons; replace with `<Icon name="lucide-name" />` (lucide is
  already the project's standard icon set via `lucide-svelte`; there
  is no carve-out for emoji as iconography).
- Add a `web/scripts/check-icons.mjs` script that walks `src/`,
  flags any file containing `<svg ` outside `$lib/Icon.svelte` or any
  Unicode emoji used as a UI glyph (allowlist: `branding/` SVGs and
  user-authored content like notes/comments).
  Wire into `npm run check` so future regressions are caught.
- Document the rule in `AGENTS.md` under a new "Iconography"
  subsection of the Design Language Tokens area.

**Acceptance:** `npm run check` runs the new icon audit clean; no
file under `web/src/routes/` or `web/src/lib/` (excluding
`Icon.svelte` and `branding/`) contains a raw `<svg>` or emoji used as
an icon.

#### Wave 10 commit & release strategy

Each sub-task A–H is its own commit and independently shippable. The
recommended ship order:

1. D (drop redundant titles) — smallest risk, biggest visual win.
2. E (Stores nav promotion) — small, isolated.
3. A (unified Add card) — touches both pages but well-scoped.
4. B (Lists DataTable) — high impact on the most-used screen.
5. C (FiltersPanel extraction) — depends on A landing first.
6. F (icon toolbar + modals) — biggest restructure; ship after the
   above are stable so regressions are easy to bisect.
7. G (Templates rewrite) — independent of F but easier to QA after
   F because users navigate to it via the new toolbar.
8. H (icon-source enforcement) — last, as cleanup + guard rail.

Ship A–F as a single `0.22.0` release; G follows as `0.22.1`; H
follows as `0.22.2`. Reserve `0.23.0` for the next wave
(per-collection themes, Phase 17 carry-in).

**Wave 10 acceptance:** all eight sub-tasks shipped; the Add card,
Items table, Filters panel, and sub-page navigation feel identical
across `/collections/[id]` and `/lists/[type]`; no inline tab content
pushes items off-screen; Templates page communicates "custom fields"
clearly with scrapers as an opt-in starter; no raw `<svg>` or emoji
icons outside `Icon.svelte`.

### Out of scope for Phase 14

Tracked separately so they don't bloat this phase:

- **Custom Tangible logo / app icon.** The current SVG is functional
  but generic. Best produced by a dedicated image-generation model
  (Midjourney / DALL-E / Stable Diffusion). Once the brand palette is
  locked in Wave 1, draft a prompt with negative prompts (e.g.
  "minimalist mark for a self-hosted home inventory app, indigo
  violet accent #7C5CFF on warm off-white #FAFAF7, geometric stacked
  cubes or container motif, flat vector, no text, no shadows, no
  gradients; negative: photorealism, 3d render, busy detail, generic
  cloud icon, warehouse photo"). Replace
  `web/static/favicon.svg` and `icon-512.png` once delivered.
- **Per-collection visual themes** (Bookshelf / Game room / Movie
  room) — see Phase 17. Requires generated background imagery; same
  delegation pattern as the logo work above.
- **Real-time collaboration** — see Phase 17.

---



Long-term work that makes Tangible a foundation other things build on.

- **Two-factor auth (TOTP)** ✅ for local accounts — setup QR code + secret in
  Settings, 8 backup codes on activation, second-step prompt on login,
  regenerate/disable flow. FIDO2/passkey remains a stretch goal.
- **Account deletion & data export self-service** ✅ — GDPR-friendly: user
  downloads all their data (JSON backup + README ZIP via `GET /auth/me/export`,
  compatible with `tangible restore` and the web import wizard), then deletes
  account via `DELETE /auth/me` (requires password + TOTP if enabled).
- **MCP server** ✅ — Model Context Protocol server mounted at `/mcp`.
  Exposes tools (`list_collections`, `search_items`, `get_item`,
  `list_maintenance`, `list_due_alerts`, `list_low_stock`) over the
  streamable HTTP transport. Auth via Bearer API token or session cookie.
  AI assistants can answer "do I have a spare furnace filter?" or
  "when is my car's next oil change?".
- **Plugin / adapter system for metadata scrapers** ✅ — community can
  contribute scrapers for new sources without modifying core. Declare adapters
  via `tangible.scraper_adapter` / `tangible.barcode_adapter` entry-point groups;
  auto-discovered at startup. `GET /metadata/adapters` lists active adapters
  (admin). Full entry-points discovery with broken-plugin resilience.
- **Item comment threads** ✅ — threaded, time-stamped annotations on
  items beyond the single `notes` field. Multi-user: household members
  can ask questions, record observations, or flag issues. One level of
  replies; any collection member can read/post; authors edit/delete own;
  editors/owners delete any comment. Full web UI with toggle panel per item.
- **i18n & localization** ✅ — svelte-i18n installed; message catalogs for EN,
  FR, DE, ES, JA in `web/src/lib/locales/`. Language picker in nav bar; locale
  persisted in localStorage; `<html lang>` updated reactively. Navigation and
  auth pages fully translated. Remaining pages use English strings pending
  community contribution.
- **Drag-and-drop photo reorder** ✅ — reorder the photo gallery by
  dragging thumbnails; server persists sort_order per photo.
- **Server-side thumbnail generation** ✅ — generate resized thumbnails on
  upload; serve via `GET /photos/{id}/thumbnail`; web and Android use
  thumbnails in lists to reduce bandwidth.
- **Autofill custom fields (type-ahead)** ✅ — when entering a value in a
  template custom field, suggest values already used in that field
  across the collection.
- **AND/OR toggle for multi-tag filters** ✅ — when multiple tags are
  selected in the collection filter bar, a toggle switches between
  "match all" (AND, default) and "match any" (OR).
- **Custom sort field** ✅ — user-assigned integer on items for manual
  ordering within a collection, independent of any data field.
  Drag-to-reorder in the web item list persists this field.

> **iOS app:** deferred indefinitely. Apple's developer program
> requirements make distribution costly for a self-hosted open-source
> app. Users on iPhone/iPad can use the responsive mobile web UI.
> Reverse-proxy and IDP (Caddy, Traefik, nginx, Authentik, Keycloak)
> setup is covered in the [admin guide](docs/admin-guide.md) rather
> than as Compose examples — most self-hosters already run their own
> proxy stack.

---

## Phase 16 — Shopping Lists expansion (planned)

The Grocery List feature becomes a general-purpose shopping and want-tracking
hub. A new **Lists** menu in the nav replaces the single "Grocery List" link
and exposes four list types: **Groceries**, **Hardware**, **Home Goods**, and
**Wish Lists**. All four share the same underlying model and API; the type
field drives category presets, auto-created backing collections, and per-list
UI copy.

### Step 0 — Rename grocery internals to shopping

The current internals are named after groceries even though they will now
carry hardware and home-goods items. Rename throughout before adding new
behaviour so the codebase stays coherent:

- **Server models** — `GroceryItem` → `ShoppingItem`, `GroceryStore` →
  `ShoppingStore`, `GroceryStoreAisle` → `ShoppingStoreAisle`. Table names
  stay as-is (no Alembic migration needed for a Python rename only).
- **Server schemas** — `GroceryItemCreate/Read/Update` →
  `ShoppingItemCreate/Read/Update`; likewise `GroceryStore*` →
  `ShoppingStore*`; `GroceryAisle*` → `ShoppingAisle*`; `GroceryCount` →
  `ShoppingCount`; `GroceryFeedEntry` → `ShoppingFeedEntry`;
  `GroceryPurchaseRequest` → `ShoppingPurchaseRequest`;
  `GrocerySource` → `ShoppingSource`.
- **Server API** — rename `api/grocery.py` → `api/shopping.py`; change the
  router prefix from `/grocery` to `/lists`. Mount the old prefix at
  `/grocery` as a redirect shim so existing Android clients and any external
  scripts continue to work during the transition.
- **MCP tool** — `list_grocery` → `list_shopping_items` (also covered in
  Step 7).
- **Web** — rename `groceryCategories.ts` → `shoppingCategories.ts`;
  rename the `GroceryStoreManager` Svelte component to `ShoppingStoreManager`.
  Web routes stay at `/grocery-list` for now (the URL migration is Step 5).
- **Android** — rename `GroceryListScreen`, `GroceryListViewModel`,
  `GroceryRepository`, `GroceryItem` data class, and `GroceryDao` to
  their `Shopping*` equivalents. Room database table name is kept via
  `@Entity(tableName = "grocery_items")` so no schema migration is required.
- **Tests** — update all test files that reference `GroceryItem`,
  `grocery.py`, or `/grocery` routes to use the new names; the `/grocery`
  redirect shim ensures existing HTTP-level tests still pass without
  path changes.

### Step 1 — Data model

- Add a `list_type` enum column to `ShoppingItem`:
  `groceries` (default, preserves all existing rows) | `hardware` |
  `home_goods` | `wish_list`.
- Write an Alembic migration; backfill existing rows to `groceries`.
- Extend all `ShoppingItem` API routes (`GET`, `POST`, `PATCH`, `DELETE`,
  `POST /purchase`, `GET /count`) to accept and filter on `list_type`.
  Unversioned callers default to `groceries` for backward compatibility.
- Wish List items add two optional fields: `url` (link to product page) and
  `priority` (integer 1–3: low / medium / high).

### Step 2 — Category presets

- **Groceries** — existing 17 categories (no change).
- **Hardware** — preset category chips: Adhesives & Tape, Caulk & Sealant,
  Concrete & Masonry, Electrical, Fasteners, Flooring, Hand Tools,
  Hardware & Hinges, HVAC & Filters, Lumber & Sheet Goods, Paint & Finishes,
  Plumbing, Power Tool Accessories, Safety & PPE, Storage & Organization.
- **Home Goods** — preset category chips: Bathroom, Bedding & Pillows,
  Candles & Fragrance, Cleaning Supplies, Cookware & Bakeware, Curtains &
  Blinds, Decor & Accents, Furniture, Kitchen Gadgets, Lighting, Linens &
  Towels, Outdoor & Garden, Rugs & Mats, Small Appliances, Storage.
- **Wish Lists** — no mandatory category; optional free-text tag field.
- Implement as typed constant arrays in `web/src/lib/shoppingCategories.ts`
  (replacing `groceryCategories.ts`) exported per type. Android mirrors
  the same sets in a `ShoppingCategory.kt` sealed class.

### Step 3 — Auto-created backing collections

- Each list type auto-creates a dedicated collection on first item add if
  one does not already exist: "Pantry" (groceries), "Hardware" (hardware),
  "Home Goods" (home_goods). Wish List items do not require a backing
  collection (they are intent records, not owned inventory).
- `createBackingCollection(listType)` replaces the current `createPantry()`
  helper in the web shopping page.

### Step 4 — Web navigation

- Replace the single "Grocery List" nav link with a **Lists** dropdown button.
- The dropdown shows four entries: Groceries, Hardware, Home Goods, Wish Lists.
- Each entry navigates to `/lists/[type]` (e.g. `/lists/groceries`).
- The bell-icon unread count (`GET /lists/count`) is summed across all
  four types and shown on the Lists dropdown trigger.

### Step 5 — Web list routes

- Add `/lists/[type]/+page.svelte` as the shared list page, parameterized
  by `type` from the URL segment.
- The page heading, empty-state copy, placeholder text, and category picker
  all derive from the `type` param.
- Wish List variant adds URL and Priority fields to the add form; replaces
  the "Bought" purchase action with a "Mark as gifted / received" action.
- The existing `/grocery-list` route redirects to `/lists/groceries` for
  backward compatibility (bookmarks and Android deep links still work).
- The `ShoppingStoreManager` component (renamed from `GroceryStoreManager`)
  is scoped to the groceries list type only; hardware and home-goods lists
  do not use store/aisle sorting.

### Step 6 — Android navigation

- Add a **Lists** bottom-nav entry (or drawer section) that expands into
  tabs: Groceries, Hardware, Home Goods, Wish Lists.
- The shared `ShoppingListScreen` (renamed from `GroceryListScreen`) is
  parameterized by `listType`; tabs switch the active type and reload the
  list. Deep links for `tangible://grocery` continue to resolve to the
  Groceries tab.
- Category picker in the add-item sheet updates its chip set based on the
  active list type.
- Wish List add sheet gains URL and Priority fields.

### Step 7 — MCP tool

- Rename `list_grocery` MCP tool to `list_shopping_items`; add optional
  `list_type` parameter so AI assistants can query any list type.

### Step 8 — i18n

- Add translation keys for all four list type names, nav label, empty-state
  messages, category chips (hardware + home goods), wish list fields
  (URL, priority, gifted/received), and the Lists dropdown in all 7 locale
  files (en, fr, de, es, it, ja, zh).

---

## Phase 17 — Polish, themes & real-time (planned)

Quality-of-life improvements that make existing features shine plus
the first steps toward live collaboration.

- **Android: unified item-row design language** — the Collections tabs item
  rows and the Shopping List rows use different visual styles today (Collections
  rows are plain `ListItem` with title + supporting text; Shopping rows show
  brand, category chip, quantity, and action buttons in a richer card style).
  Unify them: both surfaces should show the same secondary-line fields (brand,
  subtitle/notes, quantity badge, category slug) and the same trailing action
  icons, using a shared `ItemRowCard` composable. Acceptance: side-by-side
  comparison of Collections tab and Shopping List rows looks intentionally
  consistent, not accidentally different.

- **Android: "Copy or Move to shopping list" dialog** — the shopping-cart
  action on a Collections tab item row currently copies the item directly
  without giving the user a choice. Replace the single-action confirmation
  with a three-button dialog:
  - **Cancel** — dismisses without any change.
  - **Copy** — adds the item to the shopping list (current behavior), item
    stays in the collection untouched.
  - **Move** — adds the item to the shopping list AND marks the collection
    item as `depleted`, indicating it has been used up and needs restocking.
    Useful for body wash in a Pantry collection, disposable batteries in a
    Batteries collection, cleaning supplies, etc.
  The full item metadata (title, brand, `category_slug`, quantity) must be
  passed to `ShoppingRepository.addItem()` on both paths — brand was silently
  dropped before this fix. Applies to every collection type (the action is
  already present on every Collections tab row).

- **Real-time / live updates** — the app currently polls (15-min Android
  SyncWorker, manual web refresh). Add a `GET /collections/{id}/events`
  SSE (Server-Sent Events) stream that pushes `item-added`,
  `item-updated`, `item-deleted`, and `comment-added` events. The web
  client subscribes while the collection page is open and reconciles
  diffs without a full reload. Android subscribes in the foreground
  (OkHttp EventSource) and cancels when backgrounded.
- **Collection themes** — visual skins for the collection detail view
  inspired by the physical environment of each category. Three built-in
  themes to start:
  - *Bookshelf* — wood-grain shelf texture behind cover tiles; books
    stand upright as spine thumbnails.
  - *Game room* — dark ambient background with neon-accent category
    badges; cartridge/box art shown prominently.
  - *Movie room* — cinematic widescreen header; poster-style grid with
    rating stars.
  A `theme` field is added to `Collection`; the web collection detail
  page reads `collection.theme` and applies a `data-collection-theme`
  attribute for per-theme CSS; Android switches background/color tokens.
  Requires photo thumbnails in the items list API response.
  **Background imagery is delegated to a dedicated image-generation
  model** (Midjourney / DALL-E / Stable Diffusion). Each theme needs
  one tileable or stretched background per mode (light + dark). Draft
  prompts with negative prompts when commissioning, e.g. for Bookshelf:
  "wood-grain bookshelf texture, seamless tile, warm walnut tone,
  subtle vertical grain, soft natural light; negative: books, text,
  reflections, photoreal high-detail, harsh shadows, vignettes". Land
  the imagery in `web/static/themes/{name}/{mode}.webp` (and
  `android/app/src/main/res/drawable-nodpi/...`).
- **Template editing & cloning** — the server already has `ItemTemplate`
  model and CRUD API (`api/item_templates.py`); items have an optional
  `template_id` FK. Remaining work:
  - Role-based access: enforce `editor`+ for create/edit/clone, any
    member for read, using the existing `Membership` `viewer/editor/owner`
    roles.
  - `POST /item-templates/{id}/clone` endpoint.
  - Web: template management page (list, create, edit, delete, clone).
  - Android: template picker in the add-item flow.
- **Full i18n rollout** — the i18n scaffold (svelte-i18n + catalogs for
  EN/FR/DE/ES/JA) is in place. Wire the remaining web pages — collection
  list, collection detail, item detail, import wizard, settings,
  maintenance, bundles, locations — into `$_()` calls and extend all
  five catalogs. Accept community pull requests to add more locales via
  `web/src/lib/locales/`.
- **Android AI-prefill from barcode scanner** — the scanner screen today
  navigates to add-item after a scan. Wire the scanned barcode into
  `POST /api/items/ai-prefill` so the new-item form pre-populates title,
  subtitle, category, and custom fields from Open Library / MusicBrainz /
  Open Food Facts before the user sees it. Falls back gracefully if no
  match is found.

---

## Phase 18 — Universal search & discovery (in progress)

The Home page (web `/`, Android Home tab) now exposes a single search box
backed by `GET /items/search` with a "Search in" dropdown
(All / Title / Brand / Category / Notes / Barcode / Serial). Result list
shows status (Owned, Wishlist, Depleted, Archived) so a flea-market lookup
on a phone instantly answers "do I already have one?" and offers a
quick-add path when the answer is no.

Remaining work:

- **Search by tag** — extend the "Search in" dropdown with a `Tag` option.
  Server: when `field=tag`, match `Tag.name` (case-insensitive substring)
  via the existing `ItemTag` join and return items carrying that tag. UI:
  in the Home empty-state result panel, when results carry tags, render
  the tags as chips that re-run the search with `field=tag&q=<tag>`.
- **Collector value lookup for "not found" results** — when the universal
  search returns zero matches and the user is at a flea market, surface
  an inline "Look up market value" action. Adapter plug-ins per source,
  reusing the `tangible.scraper_adapter` entry-point pattern from the
  metadata scraper:
  - PriceCharting (video games, comics, trading cards, sealed media)
  - Discogs (music: vinyl, CDs)
  - eBay sold-listings / Terapeak (general second-hand)
  - IGDB (game metadata + cover art, no prices but useful for prefill)
  - Heritage Auctions (collectibles, coins)
  - Worthpoint (general antiques)
  - Numista (coins / banknotes)
  Result panel renders a price range + source links; user can one-click
  "Add to Wishlist" or "Add to a collection" pre-filled with the looked-up
  metadata. Cache lookups for 24h to be polite to upstream APIs.

---

## Phase 19 — Stack modernisation (done)

Keep the runtime dependencies current so security patches, performance
improvements, and new framework features remain accessible.

**Rule:** always fetch live versions with `npm info <pkg> version`,
`uv run pip index versions <pkg>`, or equivalent before writing any
version string. Never copy from training memory or conversation history.

### Web toolchain

| Package | Shipped in | Status |
|---|---|---|
| SvelteKit `2.8 → 2.59.1` | v0.23.0 | ✅ done |
| vite `5.4 → 6.4.2` | v0.23.0 | ✅ done (Node 18 ceiling) |
| @sveltejs/vite-plugin-svelte `4.0 → 5.1.1` | v0.23.0 | ✅ done (Node 18 ceiling) |
| Icon.js bundle `9.1 MB → 153 kB` | v0.23.0 | ✅ done (static import map) |
| **Node 18 → 20 (dev host)** | v0.24.0 | ✅ done (Node 20.19.2 on new dev host) |
| vite `6.4.2 → 8.0.11` | v0.24.0 | ✅ done |
| @sveltejs/vite-plugin-svelte `5.1.1 → 7.1.2` | v0.24.0 | ✅ done |

Steps once Node 22 is in the dev container:
1. `npm info vite version` + `npm info @sveltejs/vite-plugin-svelte version` — get live latest.
2. Check peer dep chain: `npm info @sveltejs/kit@latest peerDependencies`.
3. `npm install --save-dev vite@latest @sveltejs/vite-plugin-svelte@latest`
4. `npm run check && npm run build` — svelte-check 0 errors, build passes.
5. Bump to next patch version, CHANGELOG internal entry, commit + tag.

### Android toolchain

| Item | Current | Action |
|---|---|---|
| Compose BOM | 2026.05.00 | ✅ bumped from 2024.11.00 |
| AGP | 8.13.2 | ✅ bumped from 8.7.2 |
| Kotlin | 2.3.21 | ✅ bumped from 2.0.21 |
| KSP | 2.3.7 | ✅ bumped from 2.0.21-1.0.28 |
| Room | 2.8.4 | ✅ bumped from 2.6.1 |
| Lifecycle | 2.10.0 | ✅ bumped from 2.8.7 |
| Coil | 2.7.0 | ⬜ skip Coil 3.x (breaking API change) |
| Hilt | 2.57.2 | ✅ bumped from 2.52 (KSP 2.3.x class-loader fix) |
| hilt-navigation-compose | 1.3.0 | ✅ bumped from 1.2.0 |
| hilt-work | 1.3.0 | ✅ bumped from 1.2.0 |
| Gradle wrapper | 8.13 | ✅ bumped from 8.10.2 (required by AGP 8.13.2) |

Steps for Android bump:
1. Look up current versions on maven.google.com for each library above.
2. Update `android/gradle/libs.versions.toml`.
3. Run `./gradlew :app:lintDebug :app:testDebugUnitTest :app:assembleDebug --no-daemon`.
4. Fix any API-change errors before pushing.

### Server / Python

Python 3.12 is in active maintenance until 2028 — no urgent action.
All deps use `>=` floors and resolve to latest at install time via uv.
Re-audit when Python 3.13 support stabilises across the dep tree.

---

## Done

See [CHANGELOG.md](CHANGELOG.md) for what has shipped (auth, items,
collections, photos, tags, loans, importers, sync, web UI, Android app
with offline cache + sync worker, Docker image, CI).
