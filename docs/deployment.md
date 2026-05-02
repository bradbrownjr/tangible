# Deployment

Tangible ships as a single multi-arch (amd64/arm64) Docker image at
`ghcr.io/bradbrownjr/tangible`. The image bundles the FastAPI server and the
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
curl -fsSLO https://raw.githubusercontent.com/bradbrownjr/tangible/main/docker/docker-compose.standard.yml
docker compose -f docker-compose.standard.yml up -d
```

Then browse to <http://localhost:8000/> and register the first account —
it is automatically promoted to admin. To bootstrap headlessly instead,
set `TANGIBLE_ADMIN_USERNAME` and `TANGIBLE_ADMIN_PASSWORD` in your `.env`.

## Unraid

Pre-create the host paths:

```bash
mkdir -p /mnt/user/appdata/tangible/{data,config}
```

Drop `docker/docker-compose.unraid.yml` into your project, set
`TANGIBLE_PUBLIC_URL` to your external URL (e.g. `https://tangible.example.com`), and
bring it up. The image runs as `99:100` (`nobody:users`) by default.

The container expects to be behind a reverse proxy; pair it with Caddy:

```caddy
tangible.example.com {
    reverse_proxy tangible:8000
}
```

Make sure `tangible` and your Caddy container share an external Docker network
(`TANGIBLE_NETWORK`, default `proxy`).

## Postgres

Use the `postgres.yml` overlay alongside the standard file:

```bash
docker compose \
  -f docker/docker-compose.standard.yml \
  -f docker/docker-compose.postgres.yml up -d
```

Or set `TANGIBLE_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/tangible`
manually against an existing database.

## Backup

The `/data` volume contains:

- `tangible.db` (SQLite) and the `tangible.db-wal` / `tangible.db-shm` sidecars
- `photos/<sha[0:2]>/<sha>` — content-addressed photo files

The `/config` volume contains:

- `secret.key` — session/cookie signing key (regenerate to invalidate sessions)
- `tangible.yaml` / `tangible.env` — optional config overrides

A logical export (no photos) is available at any time:

```bash
docker exec tangible tangible backup <username> - > tangible-backup.json
```

Restore with:

```bash
docker exec -i tangible tangible restore <username> - < tangible-backup.json
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
`TANGIBLE_DB_AUTO_MIGRATE=false`.

## Health & observability

- `GET /healthz` — liveness/readiness probe (used by container HEALTHCHECK)
- `GET /version` — build metadata
- Logs use structlog; set `TANGIBLE_LOG_FORMAT=json` for machine-readable output.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Permission denied` on `/data` | PUID/PGID mismatch with the host. Set `PUID`/`PGID` env vars to match your user. |
| `403` from `/auth/login` behind Caddy | Set `TANGIBLE_BEHIND_PROXY=true` and `TANGIBLE_ALLOWED_HOSTS=<domain>`. |
| Cookies not persisting | If serving over HTTPS, ensure `TANGIBLE_FORCE_HTTPS=true` (default when `PUBLIC_URL` is `https://`). |
| Web UI 404s on refresh | The image's SPA fallback handles this; if you proxy to a subpath, use a top-level domain instead — Tangible does not yet support sub-path mounting. |
