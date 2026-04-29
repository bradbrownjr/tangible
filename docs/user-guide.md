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

Click **New item** in a collection. The form starts with a **type**
picker (vinyl, CD, tape, movie, game, console, Funko, Pokémon card,
book, tool, spice, generic). Each type has tailored default fields and
identifiers; the **generic** type lets you fill out anything.

### Quick creation tricks

- **Scrape URL** — paste a product URL (Open Library ISBN page, a
  publisher's product page) and Covet will pre-fill `title`,
  `description`, `image_url`, etc. via the metadata scraper.
- **Apply a template** — pick a template defined for the collection
  to inherit a custom-field schema. Required fields are validated on
  save; `select` fields are constrained to their option list.
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

Items themselves also have an **expires_at**. The
**Expiring** dashboard surfaces every item *and* document whose
expiry is within a window you choose, so you can see warranties about
to lapse or licenses due for renewal.

### Maintenance schedules

For tools / appliances / vehicles, add a **maintenance task** with an
**interval (in days)**. When you click **Mark complete**, Covet stores
`last_completed_at` and recomputes `next_due_at`. The
**Maintenance — due soon** dashboard lists tasks coming up across
all your collections.

### Loans

Mark an item as **lent out** to a contact. Set an optional due date.
Loans are returned by closing them; loan history stays on the item.

## Tags and search

- Add tags from the item editor or the collection's **Tags** page.
- The collection list view supports `search=` (title prefix) and
  `type=` filters.
- Filter by tag from the collection page.

## Importing your existing inventory

Open **Import** from the top nav.

- **CLZ products export** — drop the JSON file from the *Movie / Music
  / Book / Game Collector* desktop apps. Covet maps fields and creates
  items in the chosen collection.
- **Generic CSV** — upload any CSV; you'll get a column-mapping wizard
  that lets you map source columns to Covet fields (with a preview).
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
5. A **sync worker** runs every 15 minutes (and immediately when you
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
