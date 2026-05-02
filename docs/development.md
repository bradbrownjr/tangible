# Development

Tangible is a monorepo with three primary subprojects: `server/` (Python /
FastAPI), `web/` (SvelteKit), and `android/` (Kotlin / Jetpack Compose).

## Prerequisites

- Python 3.12+ and [uv](https://github.com/astral-sh/uv)
- Node.js 20+ and `pnpm`
- JDK 17+ and Android SDK (for the mobile app)
- Docker (for running databases and integration tests)

## Server

```bash
cd server
uv sync
uv run alembic upgrade head
uv run uvicorn tangible.main:app --reload
```

Default URL: <http://localhost:8000>. OpenAPI docs at `/docs`.

Run tests:

```bash
uv run pytest
```

## Web

```bash
cd web
pnpm install
pnpm dev
```

Default URL: <http://localhost:5173>. Set `VITE_TANGIBLE_API_URL=http://localhost:8000`
in `web/.env.local` if your server runs elsewhere.

## Android

Open `android/` in Android Studio (Hedgehog or newer) and run the `app`
configuration on an emulator or device. The default server URL can be set in
the in-app onboarding screen.

## Configuration

All server configuration is documented in [configuration.md](configuration.md).
