# Installing Tangible on Android

Tangible is distributed as an APK (Android application package). It is not
currently available on the Google Play Store. There are two supported ways to
install it: **Obtanium** (recommended — keeps the app up to date
automatically) and manual **sideloading**.

---

## Option 1 — Obtanium (recommended)

[Obtanium](https://github.com/ImranR98/Obtainium) is a free, open-source
update manager that installs and updates apps directly from their GitHub
releases. It handles signing-consistency checks and notifies you when a new
version is available.

### Steps

1. Install Obtanium from its own [GitHub releases page](https://github.com/ImranR98/Obtainium/releases)
   or from F-Droid.
2. Open Obtanium and tap **Add App**.
3. Paste the Tangible repository URL:
   ```
   https://github.com/bradbrownjr/tangible
   ```
4. Under **APK filter**, enter `tangible-` so Obtanium only considers the Tangible
   APK and ignores any other attached assets.
5. Tap **Add** — Obtanium will find the latest release and offer to install
   it.
6. Tap **Install** and follow the on-device prompts.

### Subsequent updates

Open Obtanium and tap **Check for updates** (or enable background checks in
its settings). Tangible will appear in the list when a new version is
available; tap **Update** to install it.

---

## Option 2 — Manual sideloading

1. Go to the [Tangible releases page](https://github.com/bradbrownjr/tangible/releases).
2. Under the latest release, expand **Assets** and download `tangible-X.Y.Z.apk`
   (the file ending in `.apk`, not `.zip` or `.aab`).
3. On your Android device, open the **Files** app (or a file manager) and
   navigate to your **Downloads** folder.
4. Tap the APK file. Android will ask you to allow installation from this
   source — tap **Settings**, enable **Install unknown apps**, then return
   and tap **Install**.
5. Tap **Open** once installation completes.

To update manually, repeat these steps. Android will replace the existing
installation because the APK is signed with the same key.

---

## Device-specific notes

### Samsung / Knox devices

Samsung devices run an **AV scan** before installing unknown APKs. This is
normal — the scan is performed by Samsung's McAfee integration and takes a
few seconds. Once it completes you will see an **Install** button. There is
no need to disable any security setting; the scan runs automatically and
does not block the installation.

If you see a **"Blocked by Play Protect"** warning, tap **Install anyway**
— this warning appears for any app not distributed via the Play Store and
does not mean the app is unsafe.

### Required permissions

Tangible will request the following permissions on first use:

| Permission | Used for |
|---|---|
| **Internet** | Connecting to your Tangible server |
| **Camera** | Barcode / QR-code scanning |
| **Read media images** | Uploading photos from your gallery |

All permissions are optional at install time. Camera and media access can be
granted later in **Android Settings → Apps → Tangible → Permissions**.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "App not installed" error | Ensure you have enough storage space; try rebooting and reinstalling. |
| "There is a problem parsing the package" | The download was corrupted — re-download the APK. |
| Obtanium shows two APK options | Choose the file named `tangible-X.Y.Z.apk`; ignore any file with `-release-unsigned` in the name. |
| Connection refused after install | Open the app, go to **Settings**, and verify the server URL is correct (include `http://` or `https://`). |
