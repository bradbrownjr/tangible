# Configuration reference

All settings are loaded from environment variables (prefix `TANGIBLE_`) with
overrides from `${TANGIBLE_CONFIG_DIR}/tangible.env` and `tangible.yaml`. Secrets
support a `<NAME>_FILE` convention for Docker secrets and Unraid file
mounts.

## Core / runtime

| Variable               | Default       | Notes                                   |
| ---------------------- | ------------- | --------------------------------------- |
| `TANGIBLE_DATA_DIR`       | `/data`       | Photos, SQLite db, uploads              |
| `TANGIBLE_CONFIG_DIR`     | `/config`     | Optional config files, secret.key       |
| `TANGIBLE_HOST`           | `0.0.0.0`     |                                         |
| `TANGIBLE_PORT`           | `8000`        |                                         |
| `TANGIBLE_LOG_LEVEL`      | `INFO`        | `DEBUG`, `INFO`, `WARNING`, `ERROR`     |
| `TANGIBLE_LOG_FORMAT`     | `console`     | `console` or `json`                      |
| `TANGIBLE_TZ`             | `UTC`         | IANA timezone name                       |
| `PUID` / `PGID`        | `1000`/`1000` | Container user (Unraid image: `99/100`) |
| `UMASK`                | `0022`        |                                         |

## Database

Provide a single SQLAlchemy URL **or** discrete fields:

```env
TANGIBLE_DATABASE_URL=postgresql+psycopg://tangible:secret@db:5432/tangible
```

| Variable                       | Default | Notes                                                     |
| ------------------------------ | ------- | --------------------------------------------------------- |
| `TANGIBLE_DATABASE_URL`           | —       | Full SQLAlchemy URL; overrides discrete fields           |
| `TANGIBLE_DB_TYPE`                | `sqlite`| `sqlite`, `postgresql`, `mysql`, `mariadb`                |
| `TANGIBLE_DB_HOST`                | —       |                                                           |
| `TANGIBLE_DB_PORT`                | —       | Auto-defaults per type                                    |
| `TANGIBLE_DB_NAME`                | `tangible` | Database name (Tangible manages tables itself)               |
| `TANGIBLE_DB_USER`                | —       |                                                           |
| `TANGIBLE_DB_PASSWORD`            | —       | Use `TANGIBLE_DB_PASSWORD_FILE` for Docker secrets           |
| `TANGIBLE_DB_SSLMODE`             | —       | Passthrough where supported                                |
| `TANGIBLE_DB_POOL_SIZE`           | `5`     |                                                           |
| `TANGIBLE_DB_POOL_MAX_OVERFLOW`   | `10`    |                                                           |
| `TANGIBLE_DB_AUTO_MIGRATE`        | `true`  | Run Alembic on startup                                    |

## Reverse proxy / public URL

| Variable                  | Default                              | Notes                                       |
| ------------------------- | ------------------------------------ | ------------------------------------------- |
| `TANGIBLE_PUBLIC_URL`        | `http://localhost:8000`              | Used for OIDC redirects, share links, CORS  |
| `TANGIBLE_BEHIND_PROXY`      | `false`                              | Trust `X-Forwarded-*` headers               |
| `TANGIBLE_TRUSTED_PROXIES`   | RFC1918 ranges                       | Comma-separated CIDRs                       |
| `TANGIBLE_FORCE_HTTPS`       | auto (true if PUBLIC_URL is https)   |                                             |
| `TANGIBLE_CORS_ORIGINS`      | `${PUBLIC_URL}`                      | Comma-separated                             |
| `TANGIBLE_ALLOWED_HOSTS`     | derived from PUBLIC_URL host         | Comma-separated host header allowlist        |

### Caddy example

```caddyfile
tangible.example.com {
    reverse_proxy tangible:8000
}
```

Pair with:

```env
TANGIBLE_PUBLIC_URL=https://tangible.example.com
TANGIBLE_BEHIND_PROXY=true
TANGIBLE_ALLOWED_HOSTS=tangible.example.com
```

## Sessions / auth

| Variable                          | Default         | Notes                                          |
| --------------------------------- | --------------- | ---------------------------------------------- |
| `TANGIBLE_SECRET_KEY`                | auto-generated  | Persisted to `${CONFIG_DIR}/secret.key` if unset |
| `TANGIBLE_SESSION_COOKIE_NAME`       | `tangible_session` |                                                |
| `TANGIBLE_SESSION_COOKIE_SECURE`     | auto            | Defaults from `FORCE_HTTPS`                    |
| `TANGIBLE_SESSION_COOKIE_SAMESITE`   | `lax`           |                                                |
| `TANGIBLE_SESSION_TTL_HOURS`         | `720`           |                                                |
| `TANGIBLE_REGISTRATION_ENABLED`      | `false`         | First registered user is always promoted to admin |
| `TANGIBLE_PASSWORD_MIN_LENGTH`       | `12`            |                                                |

## OIDC / OAuth (optional)

Master toggles:

| Variable                          | Default   |
| --------------------------------- | --------- |
| `TANGIBLE_OIDC_ENABLED`              | `false`   |
| `TANGIBLE_OIDC_AUTO_CREATE_USERS`    | `true`    |
| `TANGIBLE_OIDC_DEFAULT_ROLE`         | `viewer`  |

Per-provider (replace `<NAME>`, e.g. `AUTHENTIK`, `GOOGLE`):

| Variable                                   | Default                                               |
| ------------------------------------------ | ----------------------------------------------------- |
| `TANGIBLE_OIDC_<NAME>_DISPLAY_NAME`           | `<NAME>`                                              |
| `TANGIBLE_OIDC_<NAME>_ISSUER`                 | required                                              |
| `TANGIBLE_OIDC_<NAME>_CLIENT_ID`              | required                                              |
| `TANGIBLE_OIDC_<NAME>_CLIENT_SECRET`          | required (or `_FILE`)                                 |
| `TANGIBLE_OIDC_<NAME>_SCOPES`                 | `openid profile email`                                |
| `TANGIBLE_OIDC_<NAME>_REDIRECT_URI`           | `${PUBLIC_URL}/auth/oidc/<name>/callback`             |
| `TANGIBLE_OIDC_<NAME>_ADMIN_GROUPS`           | comma-separated group claims auto-granted admin       |
| `TANGIBLE_OIDC_<NAME>_USERNAME_CLAIM`         | `preferred_username`                                  |

## Photo storage

| Variable                          | Default                  |
| --------------------------------- | ------------------------ |
| `TANGIBLE_PHOTOS_DIR`                | `${DATA_DIR}/photos`     |
| `TANGIBLE_PHOTOS_MAX_BYTES`          | `26214400` (25 MiB)      |
| `TANGIBLE_PHOTOS_THUMBNAIL_SIZES`    | `256,1024`               |

## Sync

| Variable                          | Default |
| --------------------------------- | ------- |
| `TANGIBLE_SYNC_SNAPSHOT_INTERVAL`    | `100`   |
| `TANGIBLE_SYNC_RETENTION_DAYS`       | `30`    |
| `TANGIBLE_SYNC_MAX_BATCH`            | `500`   |

## Rate limiting

| Variable                   | Default       |
| -------------------------- | ------------- |
| `TANGIBLE_RATE_LIMIT_LOGIN`   | `5/minute`    |
| `TANGIBLE_RATE_LIMIT_API`     | `120/minute`  |
| `TANGIBLE_API_TOKEN_TTL_DAYS` | `0` (never)   |

## SMTP (optional, future use)

| Variable               | Default | Notes                          |
| ---------------------- | ------- | ------------------------------ |
| `TANGIBLE_SMTP_HOST`      | —       |                                |
| `TANGIBLE_SMTP_PORT`      | `587`   |                                |
| `TANGIBLE_SMTP_USER`      | —       |                                |
| `TANGIBLE_SMTP_PASSWORD`  | —       | Use `_FILE` for Docker secrets |
| `TANGIBLE_SMTP_FROM`      | —       |                                |
| `TANGIBLE_SMTP_STARTTLS`  | `true`  |                                |

## First-run admin bootstrap

These variables are **optional**. If both are set on first launch the
admin user is created from env. If you leave them unset, browse to the
UI and register — the first account to sign up is auto-promoted to
admin, regardless of `TANGIBLE_REGISTRATION_ENABLED`:

| Variable                | Notes                          |
| ----------------------- | ------------------------------ |
| `TANGIBLE_ADMIN_USERNAME`  |                                |
| `TANGIBLE_ADMIN_PASSWORD`  | Use `_FILE` for Docker secrets |
| `TANGIBLE_ADMIN_EMAIL`     | Optional                       |

## Integration API keys

These can also be set in the admin UI; environment values take precedence.

| Variable                            | Notes                                        |
| ----------------------------------- | -------------------------------------------- |
| `TANGIBLE_DISCOGS_TOKEN`               | Personal access token                        |
| `TANGIBLE_TMDB_API_KEY`                |                                              |
| `TANGIBLE_IGDB_CLIENT_ID`              |                                              |
| `TANGIBLE_IGDB_CLIENT_SECRET`          | Use `_FILE` for Docker secrets               |
| `TANGIBLE_MUSICBRAINZ_USER_AGENT`      | Default `Tangible/1.0 (+${PUBLIC_URL})`         |
| `TANGIBLE_UPCITEMDB_KEY`               | Optional fallback for unknown barcodes       |
