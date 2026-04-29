# Covet Android

Native Android client (Kotlin + Jetpack Compose + Hilt + Retrofit + Room).

## Requirements

- Android Studio Ladybug (2024.2.1) or newer
- JDK 17
- Android SDK with platform-35

## First-time setup

The Gradle wrapper JAR is **not** committed to the repo. Generate it once:

```bash
cd android
gradle wrapper --gradle-version 8.10.2 --distribution-type bin
```

(Android Studio will do this automatically on first sync.)

## Build

```bash
./gradlew :app:assembleDebug
# APK lands in app/build/outputs/apk/debug/
```

## Run on device / emulator

Open the `android/` directory as a project in Android Studio and hit Run, or:

```bash
./gradlew :app:installDebug
adb shell am start -n io.github.bradbrownjr.covet.debug/io.github.bradbrownjr.covet.MainActivity
```

## Tests

```bash
./gradlew :app:testDebugUnitTest
./gradlew :app:connectedDebugAndroidTest   # needs an emulator/device
```

## App layout

```
app/src/main/java/io/github/bradbrownjr/covet/
├── CovetApp.kt                — Application + Hilt + WorkManager bootstrap
├── MainActivity.kt
├── data/
│   ├── auth/SessionStore.kt   — DataStore-backed (server URL + bearer token)
│   ├── remote/                — Retrofit API + DTOs + AuthInterceptor
│   └── repo/                  — Auth/Collection/Item repositories
├── di/NetworkModule.kt        — Moshi/OkHttp/Retrofit Hilt providers
└── ui/
    ├── theme/Theme.kt
    ├── CovetApp.kt            — root NavHost
    └── screen/
        ├── login/             — server URL + credentials
        ├── collections/       — list + create
        ├── collection/        — items list + add/delete
        ├── scan/              — CameraX + ML Kit barcode preview
        └── settings/          — sign out
```

## Status (v0.1.0 / Phase 5)

Implemented:

- Sign in to a Covet server (URL + username + password) → server returns a session
  cookie, client immediately mints a long-lived API token via `POST /auth/tokens`
- Browse collections, create new collection
- View items in a collection, add an item, delete an item
- Camera barcode preview (EAN-13/EAN-8/UPC-A/UPC-E/Code-128/QR) — currently
  pops back to the previous screen with the scanned value (no metadata lookup yet)
- Sign out

Deferred (tracked as v1 follow-ups):

- Room cache + offline-first writes
- Sync worker with CRDT change uploads (`POST /collections/{id}/sync/push`)
- Photo capture / attach
- Loan widget
- Metadata lookup (Discogs / TMDB / IGDB / OpenLibrary / MusicBrainz) once
  server-side adapter endpoints exist
- OIDC sign-in via Custom Tabs
