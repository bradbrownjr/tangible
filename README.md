# Covet

Self-hosted personal inventory management for collectibles, tools, spices —
anything you want to keep track of. Built for collectors who need to check
their inventory in the wild (a record store, a garage sale) without an
internet connection.

- **Offline-first** Android app with CRDT-based sync
- **Web UI** for management at home
- **Multi-user** with local accounts and OIDC/SSO
- **Pluggable database**: SQLite, PostgreSQL, MySQL/MariaDB
- **Imports** from CLZ products, generic CSV (with column mapping), and
  Covet JSON backups
- **Exports** to CSV and JSON
- **Self-hosted**, container-first (Docker/Unraid)

> Status: pre-alpha. Active development.

## Repository layout

| Path        | Contents                                                  |
| ----------- | --------------------------------------------------------- |
| `server/`   | FastAPI backend (Python 3.12), importers, sync engine     |
| `web/`      | SvelteKit web UI                                          |
| `android/`  | Native Android app (Kotlin + Jetpack Compose + Room)      |
| `shared/`   | Shared schemas; generated OpenAPI clients land here        |
| `docker/`   | `Dockerfile`, compose examples, Caddy snippet              |
| `docs/`     | User and developer documentation                           |

## Documentation

- [User guide](docs/user-guide.md) — collections, items, photos,
  templates, sharing, sync, mobile app
- [Admin guide](docs/admin-guide.md) — first-run setup, users &
  invitations, OIDC/SSO, backups, upgrades, observability
- [Deployment guide](docs/deployment.md) — Docker, Unraid, Postgres,
  reverse proxy
- [Configuration reference](docs/configuration.md) — every
  `COVET_*` environment variable
- [Development guide](docs/development.md) — running the stack locally

## Quick start (development)

See [docs/development.md](docs/development.md).

## Deployment

- [Deployment guide](docs/deployment.md)
- Standard Docker: [docker/docker-compose.standard.yml](docker/docker-compose.standard.yml)
- Unraid: [docker/docker-compose.unraid.yml](docker/docker-compose.unraid.yml)
- With PostgreSQL: [docker/docker-compose.postgres.yml](docker/docker-compose.postgres.yml)

## License

[Apache License 2.0](LICENSE)
