# Tangible for Android — User Guide

Tangible is a personal collection tracker. The Android app gives you offline
access to your collections and lets you add items by scanning barcodes,
looking up ISBNs, or typing a title directly.

> For installation instructions see [android-install.md](android-install.md).

---

## First launch — connecting to your server

1. Open Tangible. You will see a **Login** screen.
2. Enter your **Server URL** (e.g. `https://tangible.example.com`).
3. Enter your **username** and **password**, then tap **Sign in**.

The app validates the connection and saves the URL for future sessions. If
you see a "tangible.invalid" error, the URL field may be empty — go back and
re-enter it.

---

## Collections list

After signing in you land on the **Collections** screen.

- **Pull down** to refresh the list from the server.
- Tap the **hamburger menu** (top-right) to access Grocery List, Maintenance, Settings, About, and Help.
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
the same toolbar. Tangible scans the saved image for a barcode and runs the same
candidate lookup flow.

---

## Maintenance

Access **Maintenance** from the hamburger menu on the Collections screen. It shows all upcoming and overdue alerts across every collection:

- **Time window chips** (7d / 14d / 30d / 60d / 90d) — narrow or widen the look-ahead window.
- **Kind filter chips** — tap any alert kind (Maintenance, Chore, Low stock, etc.) to show only that category.
- **Overdue** alerts are highlighted in red with the number of days past due.
- Tap **Refresh** to re-fetch alerts from the server.

### Daily alert notifications

The app checks for alerts within your configured lead time once per day in the background (when the device has network). If any alerts are found for kinds where **App** notifications are enabled, a single grouped notification appears in the system tray. Tapping it opens the Maintenance screen.

- **Android 13+:** The app asks for notification permission on first launch. Without it, daily notifications are silently suppressed but the Maintenance screen still works.
- **No setup required by the server admin** — this uses Android's built-in alarm system, not Firebase.

---

## Settings

Access Settings from the hamburger menu on the Collections screen.

- **Server URL** — the address of your Tangible server.
- **Test connection** — pings the server and reports the result.
- **Notifications** — per-kind toggle for **App** push notifications. Enable or disable each alert kind (maintenance, chores, expiry, etc.) independently. The toggle here controls whether the daily background job posts a notification for that kind; web browser and email channels are managed in the web settings.
- **Sign out** — clears your session.

---

## About

The About screen (hamburger menu → About) shows:

- The installed app version.
- A link to the source repository at [github.com/bradbrownjr/tangible](https://github.com/bradbrownjr/tangible).
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
**Android Settings → Apps → Tangible → Permissions**.
