# Deployment

Covet ships as a single multi-arch (amd64/arm64) Docker image at
`ghcr.io/bradbrownjr/covet`. The image bundles the FastAPI server and the
SvelteKit web SPA — the API and UI share one port.

> Once the container is up, see the [Admin guide](admin-guide.md) for
> first-run setup, users, SSO, backups and upgrades. End-user docs live
> in the [User guide](user-guide.md). Every environment variable is in
> the [Configuration reference](configuration.md).

Tags:

- `:edge` — built from `main` on every push
- `:0.x.y` / `:0.x` / `:0` — published from `vX.Y.Z` git tags
- `:sha-<short>` — every commit on `main`

## Quick start (SQLite, single host)

```bash
curl -fsSLO https://raw.githubusercontent.com/bradbrownjr/covet/main/docker/docker-compose.standard.yml
docker compose -f docker-compose.standard.yml up -d
```

Then browse to <http://localhost:8000/> and complete first-run setup. Set
`COVET_ADMIN_USERNAME` and `COVET_ADMIN_PASSWORD` in your `.env` to skip the
wizard and bootstrap the initial admin automatically.

## Unraid

Pre-create the host paths:

```bash
mkdir -p /mnt/user/appdata/covet/{data,config}
```

Drop `docker/docker-compose.unraid.yml` into your project, set
`COVET_PUBLIC_URL` to your external URL (e.g. `https://covet.example.com`), and
bring it up. The image runs as `99:100` (`nobody:users`) by default.

The container expects to be behind a reverse proxy; pair it with Caddy:

```caddy
covet.example.com {
    reverse_proxy covet:8000
}
```

Make sure `covet` and your Caddy container share an external Docker network
(`COVET_NETWORK`, default `proxy`).

## Postgres

Use the `postgres.yml` overlay alongside the standard file:

```bash
docker compose \
  -f docker/docker-compose.standard.yml \
  -f docker/docker-compose.postgres.yml up -d
```

Or set `COVET_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/covet`
manually against an existing database.

## Backup

The `/data` volume contains:

- `covet.db` (SQLite) and the `covet.db-wal` / `covet.db-shm` sidecars
- `photos/<sha[0:2]>/<sha>` — content-addressed photo files

The `/config` volume contains:

- `secret.key` — session/cookie signing key (regenerate to invalidate sessions)
- `covet.yaml` / `covet.env` — optional config overrides

A logical export (no photos) is available at any time:

```bash
docker exec covet covet backup <username> - > covet-backup.json
```

Restore with:

```bash
docker exec -i covet covet restore <username> - < covet-backup.json
```

For full backups, snapshot the `/data` and `/config` volumes together (e.g.
`tar`, `restic`, or your filesystem's snapshot facility). When using SQLite,
stop the container or use `sqlite3 .backup` to capture a consistent file.

## Upgrading

Pull and recreate:

```bash
docker compose -f docker-compose.standard.yml pull
docker compose -f docker-compose.standard.yml up -d
```

The container runs `alembic upgrade head` on startup unless
`COVET_DB_AUTO_MIGRATE=false`.

## Health & observability

- `GET /healthz` — liveness/readiness probe (used by container HEALTHCHECK)
- `GET /version` — build metadata
- Logs use structlog; set `COVET_LOG_FORMAT=json` for machine-readable output.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Permission denied` on `/data` | PUID/PGID mismatch with the host. Set `PUID`/`PGID` env vars to match your user. |
| `403` from `/auth/login` behind Caddy | Set `COVET_BEHIND_PROXY=true` and `COVET_ALLOWED_HOSTS=<domain>`. |
| Cookies not persisting | If serving over HTTPS, ensure `COVET_FORCE_HTTPS=true` (default when `PUBLIC_URL` is `https://`). |
| Web UI 404s on refresh | The image's SPA fallback handles this; if you proxy to a subpath, use a top-level domain instead — Covet does not yet support sub-path mounting. |
