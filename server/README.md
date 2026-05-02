# Tangible server

FastAPI backend. See `../docs/development.md` for setup, `../docs/configuration.md`
for environment variables.

## Layout

```
src/tangible/
  main.py            # FastAPI app factory
  cli.py             # `tangible` console script
  config.py          # pydantic-settings
  logging.py         # structlog setup
  db.py              # SQLAlchemy engine/session
  security.py        # password hashing, secret loading
  models/            # SQLAlchemy models
  schemas/           # Pydantic request/response schemas
  api/               # FastAPI routers
  auth/              # local + OIDC auth
  importers/         # CLZ, generic CSV, JSON backup
  exporters/         # CSV, JSON backup
  metadata/          # external metadata adapters
  sync/              # CRDT sync engine
  storage/           # photo storage
alembic/             # migrations
tests/               # pytest suite
```
