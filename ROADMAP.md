# Covet Roadmap

This is a living plan, not a commitment. Order and scope shift as we learn.
For shipped work see [CHANGELOG.md](CHANGELOG.md). For agent rules see
[AGENTS.md](AGENTS.md).

Each phase groups changes that ship together as a coherent user story.
Within a phase, items are roughly ordered by leverage.

---

## Phase 8 — Make it shareable ✅

Today Covet treats every user as an island. The biggest gap vs. comparable
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
- **i18n scaffold** — moved to Phase 14 where translation rollout is
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

## Phase 11 — Become the whole-home database (in progress)

Covet starts as a collectibles tracker. This phase broadens it into a
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

**Remaining Phase 11 Features — ⏳ PENDING**
- **Location hierarchy (planned)** — replace flat location text with true
  location tree: `Home → Floor → Room → Zone → Container`. Each node is an
  entity with its own photo and QR label. Moving a container moves contents.
  This is a major data model change with cascading implications (item cascade
  deletion, location-based filters, UI for tree navigation, mobile QR scanner
  integration). Scope: database schema, migrations, API endpoints (CRUD trees,
  item relocation), web tree UI, Android integration.
- **Manual/asset bundles (planned)** — beyond per-item document uploads,
  add a reusable manual library that can store a primary manual plus
  related assets (diagrams, firmware, service sheets, parts lists), then
  link one bundle to multiple items. Scope: database model (bundles table,
  bundle_items join), API endpoints (CRUD bundles, attach/detach), web UI
  for bundle management and item → bundle linking, photo gallery for bundle
  assets.

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

## Phase 12 — Maintenance & operations hub (planned)

Core maintenance APIs and due-date alerts now exist. This phase expands
that foundation into a first-class operations center: scheduled care,
history, and proactive notifications across every asset.

- **Maintenance calendar** — a unified calendar/agenda view across all
  collections showing upcoming and overdue tasks (filter change, oil
  change, generator run, battery charge, etc.). Web widget + Android
  home screen shortcut.
- **Completion history with notes** — each mark-complete records
  odometer/hours reading, cost, technician (free text), and a note.
  History is paginated; exportable to CSV.
- **Push & email notifications** — opt-in alerts at configurable lead
  times (e.g. 7 days before, 1 day before, day-of, overdue). Delivery
  via email (SMTP) and Android push (FCM). Reuses the existing alerts
  API; adds a notification preferences table.
- **Low-stock alerts** — when a consumable item's quantity drops below
  its minimum, surface it in the alerts feed and optionally send a
  push/email. Integrates with the Pantry and Fuel categories.
- **Maintenance consumables linkage** — associate a maintenance task
  with the consumable items it depletes (e.g. an oil change deducts
  from the correct oil lot; a filter change deducts from a filter
  inventory item). Track cost of materials per task.
- **Chores & recurring household tasks** — non-item-specific tasks
  (clean gutters, test smoke detectors, drain water heater sediment,
  run generator, flush water softener) with assignee, recurrence, and
  completion log. Complements item-level maintenance.
- **Furnace filter workflow** — guided task flow for filter changes
  with a default schedule choice (every 2 months or every 3 months),
  plus custom interval; supports storing filter size/spec and linking
  to replacement filter inventory.
- **Refrigerator filter workflow** — recurring schedule for internal
  fridge water filters with part number, last changed date, next due
  date, and inventory linkage for replacement cartridges.
- **Water service filter workflow** — recurring schedule for
  whole-home/under-sink filtration service with stage-specific part
  numbers, last serviced date, next due date, and inventory linkage for
  replacement cartridges/canisters.
- **Generator run log shortcut** — one-tap "I ran the generator today"
  action from the item detail, stamping last run date and resetting the
  overdue alert. Backed by a maintenance task completion.

---

## Phase 13 — Smart home integration & discovery (planned)

With rich data in place, Covet can become a hub that other smart home
tools query and react to.

- **Home Assistant integration** — expose a read-only REST sensor
  endpoint (or webhook push) so HA dashboards can display stock levels,
  maintenance due dates, expiring items, and battery charge status.
  Companion blueprint for automations (e.g. notify when generator run
  is overdue).
- **NFC tag support (Android)** — write a Covet item ID to an NFC
  tag; tap tag to jump directly to item detail or mark maintenance
  complete without opening the app. Use Android's NdefMessage API;
  no extra hardware required beyond cheap NFC stickers.
- **Unified physical labeling** — support NFC tags, QR code stickers,
  and barcode stickers for both items and locations. One scan action
  can identify item/location, record movement events (from/to location,
  timestamp, actor), and optionally prompt for quantity adjustments.
- **AI-assisted item creation** — snap a photo of an item (product
  label, packaging, barcode) and let an on-device or server-side model
  pre-fill title, category, and template fields. Falls back to barcode
  lookup if no model is available.
- **Insurance export bundle** — one-click ZIP: CSV of all items with
  values + purchase dates, all primary photos, all warranty/receipt
  attachments. Structured for easy hand-off to an insurance agent.
  Optionally scoped to a single collection or a selected location
  subtree.
- **Field-value hyperlink filters** — clicking a field value (brand,
  category, manufacturer, fuel type) in item detail instantly filters
  the collection to matching items. Works on both custom `attrs` fields
  and first-class fields.
- **Image gallery / "Add more images"** — beyond a single primary
  photo, support a gallery of annotated images per item (front, back,
  serial number plate, damage, accessories included). Web slideshow +
  Android swipe.

---

## Phase 14 — Platform & ecosystem (planned)

Long-term work that makes Covet a foundation other things build on.

- **i18n & localization** ✅ scaffold exists — finish string extraction,
  wire Crowdin or Weblate, ship initial translations (French, German,
  Spanish, Japanese).
- **Two-factor auth (TOTP)** for local accounts; FIDO2/passkey as
  stretch goal.
- **Account deletion & data export self-service** — GDPR-friendly: user
  initiates download of all their data (JSON + photos + docs zip), then
  deletes account.
- **MCP server** — Model Context Protocol server exposing Covet items,
  maintenance history, and stock levels as AI context. Allows AI
  assistants to answer "do I have a spare furnace filter?" or "when is
  my car's next oil change?".
- **Native iOS app** — after Android stabilizes; share the Kotlin
  Multiplatform or React Native business logic, or build SwiftUI with
  the REST API.
- **Plugin / adapter system for metadata scrapers** — community can
  contribute scrapers for new sources (Home Depot, Amazon, AutoZone,
  manufacturer portals) without modifying core.
- **Item comment threads** — threaded, time-stamped annotations on
  items beyond the single `notes` field. Multi-user: household members
  can ask questions, record observations ("I noticed the generator
  sounded rough — ran it 10 min"), or flag issues. Useful for shared
  maintenance logs. Notifications on replies.
- **Compose example: Traefik + Authentik**.

---

## Backlog (not yet phased)

Smaller items that don't slot cleanly into a phase yet:

- Duplicate item button ✅.
- Drag-and-drop reorder of photos.
- Server-side thumbnail generation pipeline.
- Autofill custom fields based on previous entries (type-ahead from
  existing values in the same collection).
- AND/OR toggle for multi-tag filters.
- Sort options (by value, by acquisition date, by custom field) ✅.
- Parent item value rollup (container value = sum of contents) ✅.
- Scan still image for barcode (vs. live camera preview only) ✅.
- Custom sort field on items (user-assigned integer for manual ordering
  within a collection, independent of any data field).

---

## Done

See [CHANGELOG.md](CHANGELOG.md) for what has shipped (auth, items,
collections, photos, tags, loans, importers, sync, web UI, Android app
with offline cache + sync worker, Docker image, CI).
