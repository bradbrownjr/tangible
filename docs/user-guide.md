# User guide

A tour of Covet from a collector's point of view: signing in, organizing
your stuff, importing existing inventories, and using the offline mobile
app.

> Looking to install or operate the server? See the
> [Admin guide](admin-guide.md) and [Deployment guide](deployment.md).

## Concepts

| Term | Meaning |
|---|---|
| **Collection** | A top-level bucket of items (e.g. *Records*, *Tools*, *Spice rack*). Members are granted roles per collection. |
| **Item** | One thing you own. Always belongs to one collection and has a `type` (vinyl, book, tool, ...). |
| **Tag** | Free-form label you can attach to items for filtering. Scoped to a collection. |
| **Template** | A reusable per-type set of custom fields (key/label/type/required/options) attached to items in a collection. |
| **Photo** | An image attached to an item. The first one is the *primary*; others are gallery shots. |
| **Document** | Any file (PDF, receipt, manual, warranty) attached to an item. Has an optional `expires_at`. |
| **Loan** | Marks an item as lent out to a contact, with an optional due date. |
| **Maintenance task** | A recurring chore on an item (oil change, calibration). Tracks last-completed and next-due dates. |
| **Member role** | `viewer` (read), `editor` (read + write), `owner` (read + write + manage members). |

## Signing in

Open the web UI at the URL your administrator gave you. If
self-registration is enabled, click **Register**. Otherwise sign in with
the credentials your admin provided, or use one of the listed SSO
buttons (Authentik, Google, Microsoft, ...).

After logging in, the **Collections** page is your home base.

### Theme

A light/dark/system toggle lives in **Settings**. Your choice is stored
in the browser and tracked by the OS when set to *system*.

## Collections

1. Click **New collection** on the Collections page.
2. Give it a name. You become the *owner*.
3. Open the collection to add items, tags, templates and members.

### Sharing

From a collection's settings panel:

- **Members** — invite an existing user by username/email and assign a
  role.
- **Invitations** — generate a shareable invite link (with optional
  expiry) for a specific role. The recipient signs up and lands in the
  collection automatically.
- **Share links** — generate a *read-only* token URL anyone can open
  without signing in. Useful for showing your collection to a friend.

Roles and links can be revoked at any time. All membership and share
events are written to the audit log (visible to owners).

## Items

Click **Add item** (or press the + button) inside a collection. The form
shows a cascading **category picker**: first choose a root category (Music,
Movies, Books, Games, Tabletop, Tools, Collectibles, …) then a
sub-category (Vinyl LP, Cassette, Blu-ray, …). Collections created with
the setup wizard pre-select the right root for you.

Phase 11 has started with a new **Home Equipment** root in the category
picker (Appliance, Generator, HVAC/Furnace/Air Handler, Water Heater,
Refrigerator, Water Service Filtration, and Sump Pump).

Phase 11 wave 1 also adds **Fuel & Chemicals** and **Vehicles** roots.
When you create a collection using one of these roots, Covet now scaffolds
starter templates automatically so you can begin with practical fields
instead of building every template from scratch.

Depending on the category, extra fields appear:

- **Creator** — Artist/Band for music, Author for books, Director for
  movies, Developer for games, Designer for tabletop games.
- **Series / subtitle** — shown for books, movies, and games.

Hit **Enter** in each field to advance to the next; after the last field
Enter submits the row and focus returns to the first field, so you can
add a whole pile of records without touching the mouse.

The list supports both a **table view** and a **grid/tile view** — toggle
between them with the icon buttons in the filter bar. Your choice is
remembered in the browser.

### Viewing and editing items

Each item row has an **Edit** button (visible to editors and owners) that
expands an inline form for title, creator, series/subtitle, condition, and
quantity. Viewers see the collection read-only.

- **Duplicate** creates a copy of an item in the same collection and
  category, carrying over identifiers and custom attributes so you can
  make small edits instead of re-entering everything.
- **Flag** marks an item for review without changing any other fields
  (for example: `verify location`, `needs photo`, `check warranty`).
  Flagged items show a badge in list and grid views. The flag clears
  automatically on the next item edit, or you can clear it directly with
  **Unflag**.
- Parent / container items can show a computed **rollup value**. If a
  kit or container has child items, Covet shows the summed value of its
  nested contents instead of only the parent row's own `current_value`.

### Quick creation tricks

- **Scrape URL** — paste a product URL (Open Library ISBN page, a
  publisher's product page) and Covet will pre-fill `title`,
  `description`, `image_url`, etc. via the metadata scraper.
- **Scan a barcode** (web or Android) — type or paste an ISBN/EAN and
  Covet looks it up via Open Library and fills in the title and category.
- **Scan a barcode from an image** — on the web add form, click
  **Scan image** and pick a photo or screenshot containing a barcode.
  Covet decodes it in the browser and runs the same lookup flow as the
  live scanner / typed barcode path.
- **Apply a template** — pick a template from the collection's
  **Templates** tab to inherit a custom-field schema. Required fields are
  validated on save; `select` fields are constrained to their option list.
- **Pick a parent** — set `parent_id` to make this item a child of
  another (e.g. a lens that belongs to a "Camera kit" parent).
  Cycles and cross-collection parents are blocked by the server.

### Photos

- Drop one or more images at once on the item page; they upload as a
  multi-file batch.
- Paste an image URL via **Add from URL**; Covet downloads it server-
  side (with SSRF protection — private/loopback hosts are rejected).
- HEIC/HEIF files (iPhone photos) are transcoded to JPEG. EXIF
  orientation is applied so the saved pixels are upright; you don't
  need to rotate before uploading.
- The first photo on an item is the *primary*. Click any other photo's
  **Set primary** to promote it. Deleting the primary auto-promotes
  the next photo.

### Documents and expiry

Attach any file (PDF, receipt, manual, warranty) up to 50 MB. Each
document can have a **label**, **category** (`manual`, `receipt`,
`warranty`, ...), and **expiry date**.

Document text is indexed for global search. Covet indexes text/PDF
content and, when OCR support is available on the server, image text
inside attachments as well.

Items themselves also have an **expires_at**. The
**Expiring** dashboard surfaces every item *and* document whose
expiry is within a window you choose, so you can see warranties about
to lapse or licenses due for renewal.

### Maintenance schedules

For tools / appliances / vehicles, add a **maintenance task** with an
**interval (in days)**. When you click **Mark complete**, Covet stores
`last_completed_at` and recomputes `next_due_at`. You can record optional
notes, cost, technician, and odometer/hours readings with each completion.
Full completion history is paginated and exportable to CSV.

You can also link consumable items to a maintenance task. When the task
is completed, linked items are automatically depleted by the configured
quantity.

The top-level **Maintenance** page shows all upcoming and overdue alerts
across every collection in one place (filter by 7 to 365-day window).

### Chores

The **Chores** tab on each collection holds recurring household tasks that
aren't tied to a specific item — clean gutters, test smoke detectors,
run generator, etc. Set an optional interval (days) and next-due date.
Clicking **Mark done** records a timestamped completion entry with optional
notes, cost, and technician, and recomputes the next due date.

### Quick-action shortcuts for home equipment

Items in specific home-equipment categories show a one-tap action button
directly on the item card (both grid and table views):

| Category | Button label | Default interval |
|---|---|---|
| HVAC / Furnace / Air Handler | Log filter change | 60 days |
| Refrigerator | Log filter change | 180 days |
| Water Service Filtration | Log filter service | 90 days |
| Generator | Ran generator today | 30 days |

Tapping the button auto-creates (or reuses) a named chore for that item and
records a completion immediately. The chore then appears in the **Chores** tab
and **Maintenance** agenda with the updated next-due date. No manual chore
setup is required.

### Low-stock alerts

Set a **minimum quantity** on any inventory item. When the item's quantity
falls at or below the minimum, it surfaces in the Maintenance alerts page
as a "low stock" alert.

### Loans

Mark an item as **lent out** to a contact. Set an optional due date.
Loans are returned by closing them; loan history stays on the item.

## Templates

Templates live under the **Templates** tab of each collection. They let
you attach a consistent set of custom fields (Pressing year, Catalog #,
Condition grade, …) to items of a particular category.

- **Editors and owners** can create, edit, and delete templates.
- **Clone** duplicates a template within the same collection — useful
  when two sub-categories share most of the same fields.
- **Viewers** can see templates but not modify them.

Field types: `text`, `number`, `boolean`, `date`, `url`, `select` (with
an option list). `select` fields can also use a **dynamic** source that
pulls values already used in that field across the collection. Each field can
be marked **required**. An Advanced JSON
editor is available for bulk editing.

Templates also support `multi_value` fields for ordered lists (for example,
multiple URLs, multiple ISBNs, or actor lists).

Templates now also support `relation` fields for linking one item to another
by item ID, with scope controls for same-collection or any-collection links.

The Templates tab also includes a **Community scraper registry** section with
curated presets. Editors/owners can import a preset with one click to create
ready-to-use templates for that collection.
Registry presets are version-controlled in the project, so community additions
or fixes can be contributed through pull requests.

## Tags and search

- Add tags from the item editor or the collection's **Tags** page.
- The collection view supports live **title search**, category filters,
  and **sort controls** for title, current value, acquisition date, or a
  custom attribute key such as `creator`.
- Search now also matches subtitle, notes, and custom-field/identifier
  content; press `/` from collection view to focus the search box quickly.
- Use the **ownership filter** to switch between all items, owned-only,
  and wanted-only rows/cards. Editors/owners can toggle an item between
  **Wanted** and **Owned** inline. Converting to **Owned** prompts for
  acquisition date and optional purchase price.
- Editors/owners can also **select multiple items** and run bulk actions
  from the collection toolbar: set wanted/owned, set depleted/in-stock,
  bulk archive/restore, bulk tag add/remove, bulk move-to-location,
  bulk lend-to-contact, or delete selected rows/cards.
- Items can be **archived** instead of deleted, with optional disposition
  details (sold/disposed/donated, date, amount, buyer, note). Archived
  items are hidden from default views and can be shown/restored via the
  archived filter in collection view.
- Filter by tag from the collection page.

## Importing your existing inventory

Open **Import** from the top nav.

- **CLZ products export** — drop the JSON file from the *Movie / Music
  / Book / Game Collector* desktop apps. Covet maps fields and creates
  items in the chosen collection.
- **Generic CSV** — upload any CSV; you'll get a column-mapping wizard
  that lets you map source columns to Covet fields (with a preview).
- **Round-trip hierarchy CSV** — from the Import page you can download a
  collection CSV export that includes stable item/parent refs, then import
  it back with `ref:item_ref`, `ref:parent_ref`, and `category_slug` mapping
  targets to preserve parent/child relationships.
- **Covet JSON backup** — restore a `covet backup` export into a
  collection.

For very large imports (10k+ rows), prefer the server-side CLI
(`covet restore`) over the web UI.

## Mobile app (Android)

The Android app is offline-first:

1. Install the APK from the project's
   [Releases page](https://github.com/bradbrownjr/covet/releases).
2. Open the app and enter your **server URL** (e.g.
   `https://covet.example.com`) plus your username/password. The app
   exchanges them for a long-lived API token.
3. Pick a collection. The app caches items locally in a Room database
   so you can browse without signal.
4. **Add items** including from the **Barcode scanner** (CameraX +
   ML Kit). Scanning an EAN/UPC pre-fills the identifier; combine with
   the URL scraper on the web side to enrich later.
5. **Scan barcodes from still images** from the Android collection
  toolbar if you already have a saved photo / screenshot instead of a
  live camera view.
6. **Pull to refresh** — swipe down on any collection's item list to
   immediately fetch the latest items from the server, without waiting
   for the background worker.
7. A **sync worker** runs every 15 minutes (and immediately when you
   open the app) to push your local edits and pull server changes
   through the CRDT sync engine.

If you previously enrolled the device against a different server,
sign out from **Settings → Account** and re-enroll.

## Backup and export

- **Per-user JSON backup**: from the server,
  `docker exec covet covet backup <username> - > backup.json` writes
  a logical export of your collections, items, tags, contacts, and
  loans. Photos and documents are not embedded — pair this with a
  filesystem snapshot of the `/data` volume for a full backup.
- **Restore**: `docker exec -i covet covet restore <username> - < backup.json`.
- **CSV / JSON of a single collection** is available from the
  collection's overflow menu.

See the [Admin guide](admin-guide.md#backups) for full-volume backup
strategies.

## API tokens and CLI access

Generate API tokens from **Settings → Tokens** for use with `curl`,
`httpie`, scripts, or the mobile app. Tokens are tied to your user and
can be revoked individually.

```bash
TOKEN=$(cat ~/.covet-token)
curl -H "Authorization: Bearer $TOKEN" https://covet.example.com/collections
```

Optional default expiry: `COVET_API_TOKEN_TTL_DAYS` (admin setting).

## Troubleshooting

| Symptom | Try |
|---|---|
| Login button gives "rate limited" | The login endpoint allows 5 attempts per minute per IP. Wait a minute or have an admin reset your password. |
| OIDC button missing | The provider isn't configured. Ask your admin or see the [Admin guide](admin-guide.md#sso--oidc). |
| "Image exceeds N bytes" on upload | Photo > 25 MB or document > 50 MB. Resize, or have an admin raise `COVET_PHOTOS_MAX_BYTES` / `COVET_DOCUMENTS_MAX_BYTES`. |
| Photo from URL fails with "host is not publicly reachable" | The URL points at a private/loopback IP. SSRF protection is intentional. Download the image and upload directly. |
| Mobile app stuck on "Syncing…" | Check that the server URL is reachable from the phone and the token hasn't been revoked. Pull-to-refresh forces a sync. |
