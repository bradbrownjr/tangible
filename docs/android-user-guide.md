# Covet for Android — User Guide

Covet is a personal collection tracker. The Android app gives you offline
access to your collections and lets you add items by scanning barcodes,
looking up ISBNs, or typing a title directly.

> For installation instructions see [android-install.md](android-install.md).

---

## First launch — connecting to your server

1. Open Covet. You will see a **Login** screen.
2. Enter your **Server URL** (e.g. `https://covet.example.com`).
3. Enter your **username** and **password**, then tap **Sign in**.

The app validates the connection and saves the URL for future sessions. If
you see a "covet.invalid" error, the URL field may be empty — go back and
re-enter it.

---

## Collections list

After signing in you land on the **Collections** screen.

- **Pull down** to refresh the list from the server.
- Tap the **hamburger menu** (top-right) to access Settings, About, and Help.
- Tap the **+** button (bottom-right) to create a new collection.

### Creating a collection

The wizard asks you to choose a **preset category** (Books, Music, Games,
etc.) or **Custom**. Pick one, then enter a name and optional description.
Collections with a preset category use context-aware field labels (e.g.
"Author" instead of "Creator" for books).

### Editing a collection

Open a collection, then tap the **pencil icon** in the top-right corner.
You can change the name, description, and default category. You must be an
**editor** or **owner** of the collection to see the edit button.

---

## Collection detail — list and grid views

Inside a collection you see all its items.

- Tap the **grid/list toggle** in the toolbar to switch between a 2-column
  photo card grid and the compact list view.
- **Pull down** to refresh items from the server.
- Tap the **🔍 search bar** and type to filter items by title (searches the
  server).
- If items span multiple categories, **filter chips** appear above the
  search bar. Tap a chip to show only items in that category.
- If an item is a container / kit with children, the list/card can show the
  **effective rolled-up value** of its nested contents.

### Bulk actions (Android)

In collection detail, use the checkboxes on list rows or grid cards to
select multiple items. The bulk action strip supports:

- **Depleted / In stock**
- **Wanted / Owned**
- **Archive / Restore**
- **Tag add / remove**
- **Move to location / clear location**
- **Lend to contact**
- **Delete**

Use **Select visible** to select all currently filtered items, and **Clear**
to reset the selection.

---

## Adding items

Tap the **+** (FAB) to open the **Add item** dialog.

| Method | How |
|---|---|
| **Barcode / QR code** | Tap the scanner icon in the toolbar before opening the dialog; the barcode lookup fills in the title automatically. |
| **Barcode from saved image** | Tap the image icon in the toolbar and choose a photo / screenshot containing a barcode. |
| **ISBN / EAN** | Type or paste the number in the **Title** field; tap **Look up** to pre-fill metadata. |
| **URL** | Paste a product page URL; tap **Look up** to scrape the title and category. |
| **Manual** | Type the title directly and tap **Add**. |

---

## Item detail

Tap any item row or card to open its detail screen.

- The **photo strip** at the top shows all attached photos.
  - Tap a photo to view it full-screen.
  - Tap the **trash** icon on a thumbnail to delete that photo.
  - Tap the **camera+** card to pick a photo from your gallery and upload it.
- Tap the **pencil icon** to edit all item fields (title, subtitle, notes,
  condition, quantity, price, currency, location).
- Tap **Save** (floppy disk icon) to commit edits to the server.

---

## Barcode scanning

Tap the **QR/barcode icon** in the collection detail toolbar to open the
camera scanner. Point at any barcode or QR code. The app sends the code to
the server, which searches several providers for a match and returns a list
of candidates. Choose one to pre-fill the add-item dialog.

If you already have a product photo or screenshot, tap the **image icon** in
the same toolbar. Covet scans the saved image for a barcode and runs the same
candidate lookup flow.

---

## Settings

Access Settings from the hamburger menu on the Collections screen.

- **Server URL** — the address of your Covet server.
- **Test connection** — pings the server and reports the result.
- **Sign out** — clears your session.

---

## About

The About screen (hamburger menu → About) shows:

- The installed app version.
- A link to the source repository at [github.com/bradbrownjr/covet](https://github.com/bradbrownjr/covet).
- A **What's new** button that loads the full changelog from your server.

---

## Offline behaviour

The app caches collections and items in an on-device Room database. You can
browse your collection offline; changes made offline (adding items, edits)
are not queued — they require a live connection to the server. A background
**sync worker** refreshes the cache every 15 minutes when the device is
online.

---

## Permissions

| Permission | Required for |
|---|---|
| Internet | All server communication |
| Camera | Barcode scanning |
| Read media images | Picking photos from the gallery to attach to items |

If you deny camera or media access you can still use the app; scanning and
photo upload will not be available until you grant the permission in
**Android Settings → Apps → Covet → Permissions**.
