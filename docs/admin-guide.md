# Admin guide

Operating Covet for one or more users: first-run setup, accounts,
SSO, backups, upgrades, observability, and routine maintenance.

> Installing the server for the first time? Start with the
> [Deployment guide](deployment.md). Looking up a specific environment
> variable? See the [Configuration reference](configuration.md).
> End-user documentation lives in the [User guide](user-guide.md).

## First-run setup

The first time the container starts:

1. The schema is created and Alembic migrations run automatically
   (unless `COVET_DB_AUTO_MIGRATE=false`).
2. If `COVET_ADMIN_USERNAME` **and** `COVET_ADMIN_PASSWORD` are set in
   the environment, that admin account is created automatically. Pair
   with `COVET_ADMIN_PASSWORD_FILE` for Docker secrets / Unraid file
   mounts.
3. Otherwise, browse to the URL and click **Register**. The very first
   user to sign up is automatically promoted to admin — even when
   `COVET_REGISTRATION_ENABLED=false`. After that initial signup, the
   normal `COVET_REGISTRATION_ENABLED` rule applies and further public
   registration is rejected with HTTP 403 unless you explicitly enable
   it.

Once an admin exists, self-registration is **off** by default. Set
`COVET_REGISTRATION_ENABLED=true` to allow open signup, or invite users
individually (see below).

## Users and roles

Covet has two layers of authorization:

- **Global role** — `admin` or `user`. Admins can manage users,
  invitations, and audit logs; ordinary users only see their own
  collections plus collections shared with them.
- **Per-collection role** — `viewer`, `editor`, `owner`. Granted by
  the collection's owner(s) via member invites or share links.

### Inviting a user

From **Admin → Users → Invite user**:

1. Enter an email address (or copy the generated link to send out-of-
   band).
2. Pick the global role (`user` is normally what you want) and an
   optional starter collection + role.
3. Send the link. The recipient signs up and lands directly in any
   collection you pre-assigned.

Invitations expire (default 7 days) and can be revoked from the same
page.

### Resetting a password

There is no email-based reset flow yet. To reset a forgotten password:

```bash
docker exec -it covet covet bootstrap-admin   # only re-creates if missing
```

For other users, use the admin UI's **Reset password** action, which
sets a one-time password the user must change on next login.

### Disabling / removing a user

Disable from the admin UI to keep their content (loans, audit trail)
intact. Deleting a user transfers ownership of their collections to
the deleting admin and removes their sessions and tokens.

## SSO / OIDC

Covet speaks OpenID Connect via Authlib. Multiple providers can be
enabled simultaneously (e.g. Authentik *and* Google).

### Minimum setup (Authentik example)

```env
COVET_OIDC_ENABLED=true
COVET_OIDC_AUTO_CREATE_USERS=true
COVET_OIDC_DEFAULT_ROLE=user

COVET_OIDC_AUTHENTIK_DISPLAY_NAME=Authentik
COVET_OIDC_AUTHENTIK_ISSUER=https://auth.example.com/application/o/covet/
COVET_OIDC_AUTHENTIK_CLIENT_ID=covet
COVET_OIDC_AUTHENTIK_CLIENT_SECRET_FILE=/run/secrets/authentik
COVET_OIDC_AUTHENTIK_ADMIN_GROUPS=covet-admins
```

The redirect URI defaults to
`${COVET_PUBLIC_URL}/auth/oidc/authentik/callback`. Register that
exact URL in your provider.

`ADMIN_GROUPS` (comma-separated group claims) auto-promotes anyone in
those groups to global admin. If not set, all OIDC users get
`COVET_OIDC_DEFAULT_ROLE`.

See the [Configuration reference](configuration.md#oidc--oauth-optional)
for every per-provider setting.

### Behind a reverse proxy

If Covet runs behind Caddy / nginx / Traefik with TLS terminated at
the proxy, you **must** set:

```env
COVET_PUBLIC_URL=https://covet.example.com
COVET_BEHIND_PROXY=true
COVET_ALLOWED_HOSTS=covet.example.com
```

Otherwise OIDC redirects, share links, cookies, and the host-header
allowlist will all be wrong. See
[Deployment guide → Caddy snippet](deployment.md#unraid).

## Backups

The `/data` volume holds your *content* and the `/config` volume holds
*secrets*. A complete backup is both volumes captured at a consistent
point in time.

### Logical (per-user) backup

Quick, portable, no photos/documents:

```bash
docker exec covet covet backup alice - > alice-2026-04-29.json
```

Restore into the same or a different deployment:

```bash
docker exec -i covet covet restore alice - < alice-2026-04-29.json
```

### Volume snapshots (recommended)

For full fidelity (photos, documents, sync state), snapshot the
volumes:

```bash
# Stop the container so SQLite is consistent (skip if using Postgres).
docker compose stop covet

tar czf covet-data-$(date +%F).tgz \
    -C /var/lib/docker/volumes/covet_data/_data . \
    -C /var/lib/docker/volumes/covet_config/_data .

docker compose start covet
```

Or use [`restic`](https://restic.net/) with hooks. With Postgres,
back up the database with `pg_dump` *and* the `/data` volume (which
still holds photos and documents).

### What to retain

| Path | Why |
|---|---|
| `/data/covet.db` (+ `-wal`, `-shm`) | SQLite database |
| `/data/photos/` | Item photos (content-addressed) |
| `/data/documents/` | Item attachments (content-addressed) |
| `/config/secret.key` | Session & cookie signing key. Lose it → all sessions invalid; logged-in users sign back in. |
| `/config/covet.yaml` / `covet.env` | Optional declarative config |

## Upgrading

```bash
docker compose pull
docker compose up -d
```

The container runs `alembic upgrade head` on start unless
`COVET_DB_AUTO_MIGRATE=false`. Always:

1. Take a backup first (see above).
2. Read the relevant section of [`CHANGELOG.md`](../CHANGELOG.md).
3. Pin to a major or minor tag (`:0.11`, `:0`) in production rather
   than `:edge`, so you don't pull breaking changes inadvertently.
4. After upgrades, review the shipped documentation set:
   `CHANGELOG.md` for release notes,
   `docs/user-guide.md` for web/server user workflows, and
   `docs/android-user-guide.md` for Android workflows.

### Recent client features with no extra server config

The following recent features are client/API behavior only and do **not**
require new environment variables or reverse-proxy changes:

- Web duplicate-item action.
- Web + API item review flags (`POST /items/{id}/flag`, `DELETE /items/{id}/flag`)
   with automatic flag clear on the next standard item edit.
- Dynamic template dropdown sources (`select_source: "dynamic"`) plus
   `GET /collections/{collection_id}/template-field-options/{field_key}` for
   deriving options from values already used across a collection.
- Multi-value template fields (`type: "multi_value"`) for ordered lists,
   with server-side coercion from either JSON arrays or comma-separated text.
- Relation template fields (`type: "relation"`) with scope control
   (`same_collection` / `any_collection`) and server-side target-item validation.
- Community scraper registry discovery/import endpoints:
   `GET /metadata/registry` and `POST /metadata/registry/import`.
- Wanted-item tracking (`wanted` boolean on items) plus
   `GET /items?wanted=true/false` filtering and inline Wanted/Owned toggles in web
   with acquisition-date / purchase-price capture when marking owned.
- Web item sort controls (title, value, acquisition date, custom field).
- Web + Android barcode scanning from still images.
- Parent/container value rollups exposed as `rollup_current_value` on item reads.

To pin a specific version:

```yaml
services:
  covet:
    image: ghcr.io/bradbrownjr/covet:0.11.0
```

### Rollback

If a migration goes badly:

1. Restore the volume snapshot taken before upgrade.
2. Re-deploy the previous image tag.
3. File a bug with the offending version + `docker logs covet` output.

## Observability

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness/readiness probe. Used by the container HEALTHCHECK. |
| `GET /readyz` | Same, with a database round-trip. |
| `GET /version` | `{"version": "X.Y.Z", "git_sha": "..."}`. |
| `GET /metrics` | Prometheus metrics: `covet_http_requests_total`, latency histograms, sync queue depth. |

Logs use [structlog](https://www.structlog.org). For machine-parseable
output:

```env
COVET_LOG_FORMAT=json
COVET_LOG_LEVEL=INFO
```

The access-log middleware emits one structured line per request with
`method`, `path`, `route`, `status`, `duration_ms`, `user_id`, and
`request_id`.

### Audit log

Owner-visible per collection; admin-visible globally from
**Admin → Audit log**. Records member changes, invitations, share-
link creation/use, role changes, and bulk imports. Retained
indefinitely; prune with `DELETE FROM audit_log_entries WHERE
created_at < ...` if you need to.

## Rate limiting

| Variable | Default | Notes |
|---|---|---|
| `COVET_RATE_LIMIT_LOGIN` | `5/minute` | Per-IP, login + register |
| `COVET_RATE_LIMIT_API` | `120/minute` | Per-token (or per-IP for unauth) |

Rate-limit hits return `429 Too Many Requests` with a
`Retry-After` header.

## Storage limits

Reject huge uploads early to protect the disk:

| Variable | Default |
|---|---|
| `COVET_PHOTOS_MAX_BYTES` | `26214400` (25 MiB) |
| `COVET_DOCUMENTS_MAX_BYTES` | `52428800` (50 MiB) |
| `COVET_PHOTOS_DIR` | `${COVET_DATA_DIR}/photos` |
| `COVET_DOCUMENTS_DIR` | `${COVET_DATA_DIR}/documents` |

Both stores are *content-addressed*: identical bytes uploaded twice
take one slot on disk. Deleting the last reference garbage-collects
the file.

## Routine tasks

### Vacuum SQLite

After bulk imports / large deletes:

```bash
docker exec covet sqlite3 /data/covet.db "VACUUM;"
```

### Rotate the session key

Replace `/config/secret.key` and restart. All sessions are invalidated;
API tokens continue to work.

### Force re-migration

```bash
docker exec covet covet migrate
```

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Container restarts in a loop | `docker logs covet` — usually a bad `COVET_*` value or migration failure. |
| 400 Bad Request on every request | `COVET_ALLOWED_HOSTS` doesn't include the host you're hitting. Loopback (`localhost`, `127.0.0.1`, `::1`) is always allowed. |
| OIDC callback returns "invalid state" | Cookies blocked by reverse-proxy stripping `Set-Cookie`, or `COVET_FORCE_HTTPS` mismatch. |
| `Permission denied` writing `/data` | `PUID`/`PGID` don't match the host owner of the volume. Adjust env vars or `chown` the volume. |
| `429` storms during import | Bulk operations should use the CLI, not the API. Or raise `COVET_RATE_LIMIT_API`. |
| OIDC button missing | Provider env vars not set or `COVET_OIDC_ENABLED=false`. Check `docker exec covet env | grep OIDC`. |
| Sync conflicts on mobile | Open the item; Covet shows both versions and lets you pick. CRDT keeps history forever in `automerge_changes`. |

## Getting help

- File issues at <https://github.com/bradbrownjr/covet/issues>.
- Include `docker exec covet covet version`, the relevant section of
  `docker logs covet`, and your sanitized `covet.env`.
