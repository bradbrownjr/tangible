# Admin guide

Operating Covet for one or more users: first-run setup, accounts,
SSO, reverse proxies, backups, upgrades, observability, and routine
maintenance.

> Installing the server for the first time? Start with the
> [Deployment guide](deployment.md). Looking up a specific environment
> variable? See the [Configuration reference](configuration.md).
> End-user documentation lives in the [User guide](user-guide.md).

## Table of contents

- [First-run setup](#first-run-setup)
- [Users and roles](#users-and-roles)
  - [Inviting a user](#inviting-a-user)
  - [Resetting a password](#resetting-a-password)
  - [Disabling / removing a user](#disabling--removing-a-user)
- [SSO / OIDC](#sso--oidc)
  - [Authentik](#authentik)
  - [Keycloak](#keycloak)
  - [Authelia](#authelia)
  - [Google / GitHub (external OAuth)](#google--github-external-oauth)
- [Reverse proxy setup](#reverse-proxy-setup)
  - [Caddy](#caddy)
  - [Traefik](#traefik)
  - [nginx](#nginx)
  - [Required Covet env vars (all proxies)](#required-covet-env-vars-all-proxies)
- [Backups](#backups)
  - [Logical backup](#logical-per-user-backup)
  - [Volume snapshots](#volume-snapshots-recommended)
  - [What to retain](#what-to-retain)
- [Upgrading](#upgrading)
  - [Recent client features with no extra server config](#recent-client-features-with-no-extra-server-config)
  - [Rollback](#rollback)
- [Observability](#observability)
  - [Audit log](#audit-log)
- [Rate limiting](#rate-limiting)
- [Storage limits](#storage-limits)
- [Routine tasks](#routine-tasks)
- [Troubleshooting](#troubleshooting)
- [Getting help](#getting-help)

---

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
enabled simultaneously (e.g. Authentik *and* Google). Set
`COVET_OIDC_ENABLED=true` to activate the system, then configure one
or more providers as shown below.

Common env vars that apply to all providers:

| Variable | Default | Notes |
|---|---|---|
| `COVET_OIDC_ENABLED` | `false` | Master switch |
| `COVET_OIDC_AUTO_CREATE_USERS` | `true` | Create local account on first login |
| `COVET_OIDC_DEFAULT_ROLE` | `user` | Role for auto-created users (`user` or `admin`) |

### Authentik

Create an OAuth2/OIDC provider in Authentik. Set the redirect URI to
`https://covet.example.com/auth/oidc/authentik/callback`.

```env
COVET_OIDC_AUTHENTIK_DISPLAY_NAME=Authentik
COVET_OIDC_AUTHENTIK_ISSUER=https://auth.example.com/application/o/covet/
COVET_OIDC_AUTHENTIK_CLIENT_ID=covet
COVET_OIDC_AUTHENTIK_CLIENT_SECRET_FILE=/run/secrets/authentik_secret
COVET_OIDC_AUTHENTIK_ADMIN_GROUPS=covet-admins
```

`ADMIN_GROUPS` (comma-separated group claims) auto-promotes anyone in
those groups to global admin. If not set, all OIDC users get
`COVET_OIDC_DEFAULT_ROLE`.

### Keycloak

Create a client in your Keycloak realm. Set **Access Type** to
`confidential` and add the redirect URI
`https://covet.example.com/auth/oidc/keycloak/callback`.

```env
COVET_OIDC_KEYCLOAK_DISPLAY_NAME=Keycloak
COVET_OIDC_KEYCLOAK_ISSUER=https://keycloak.example.com/realms/myrealm
COVET_OIDC_KEYCLOAK_CLIENT_ID=covet
COVET_OIDC_KEYCLOAK_CLIENT_SECRET_FILE=/run/secrets/keycloak_secret
COVET_OIDC_KEYCLOAK_ADMIN_GROUPS=covet-admins
```

Keycloak issues group claims as `/group-name` paths by default. The
admin-group check is a substring match, so `covet-admins` matches
`/covet-admins`.

### Authelia

Authelia acts as an OIDC provider from version 4.38+. Create a client
entry in `configuration.yml` and register the redirect URI
`https://covet.example.com/auth/oidc/authelia/callback`.

```yaml
# authelia configuration.yml excerpt
identity_providers:
  oidc:
    clients:
      - id: covet
        description: Covet
        secret: '$pbkdf2-sha512$...'   # bcrypt or pbkdf2 hash of the secret
        redirect_uris:
          - https://covet.example.com/auth/oidc/authelia/callback
        scopes: [openid, profile, email, groups]
        grant_types: [authorization_code]
```

```env
COVET_OIDC_AUTHELIA_DISPLAY_NAME=Authelia
COVET_OIDC_AUTHELIA_ISSUER=https://authelia.example.com
COVET_OIDC_AUTHELIA_CLIENT_ID=covet
COVET_OIDC_AUTHELIA_CLIENT_SECRET_FILE=/run/secrets/authelia_secret
COVET_OIDC_AUTHELIA_ADMIN_GROUPS=covet-admins
```

### Google / GitHub (external OAuth)

For households that use Google or GitHub accounts, set the redirect URI
in the provider's developer console to
`https://covet.example.com/auth/oidc/<provider>/callback`.

```env
# Google
COVET_OIDC_GOOGLE_DISPLAY_NAME=Google
COVET_OIDC_GOOGLE_ISSUER=https://accounts.google.com
COVET_OIDC_GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
COVET_OIDC_GOOGLE_CLIENT_SECRET_FILE=/run/secrets/google_secret

# GitHub
COVET_OIDC_GITHUB_DISPLAY_NAME=GitHub
COVET_OIDC_GITHUB_ISSUER=https://token.actions.githubusercontent.com
COVET_OIDC_GITHUB_CLIENT_ID=Ov23li...
COVET_OIDC_GITHUB_CLIENT_SECRET_FILE=/run/secrets/github_secret
```

GitHub does not issue an `email` scope by default — enable it in the
OAuth app settings or users will need to set a local email after first
login.

See the [Configuration reference](configuration.md#oidc--oauth-optional)
for every per-provider setting.

---

## Reverse proxy setup

Most self-hosters already run a reverse proxy. Covet sits behind it
on port 8000. All proxies must:

- Forward the real client IP via `X-Forwarded-For`.
- Pass `Host`, `X-Forwarded-Proto`, and `X-Real-IP` headers.
- Terminate TLS (Covet does not manage certificates).

### Required Covet env vars (all proxies)

Set these regardless of which proxy you use:

```env
COVET_PUBLIC_URL=https://covet.example.com
COVET_BEHIND_PROXY=true
COVET_ALLOWED_HOSTS=covet.example.com
```

Without `COVET_BEHIND_PROXY=true`, Covet ignores forwarded-IP headers
and will rate-limit your proxy's IP instead of the real clients'.
Without `COVET_ALLOWED_HOSTS`, the host-header allowlist will reject
requests for your domain with HTTP 400.

### Caddy

Caddy obtains and renews TLS automatically via Let's Encrypt or ZeroSSL.

```caddy
covet.example.com {
    encode zstd gzip
    reverse_proxy covet:8000
}
```

Place this in your `Caddyfile` (global or per-site). Covet and Caddy
must share a Docker network. A full reference snippet is also included at
[`docker/Caddyfile.example`](../docker/Caddyfile.example).

If you need the WebSocket upgrade header for future SSE support:

```caddy
covet.example.com {
    encode zstd gzip
    reverse_proxy covet:8000 {
        header_up Connection {>Connection}
        header_up Upgrade {>Upgrade}
    }
}
```

### Traefik

Add Traefik labels to the Covet service in your Compose file. This
assumes a Traefik instance already running with a `proxy` external
network and an `https` entrypoint:

```yaml
services:
  covet:
    image: ghcr.io/bradbrownjr/covet:0
    networks:
      - proxy
      - default
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.covet.rule=Host(`covet.example.com`)"
      - "traefik.http.routers.covet.entrypoints=https"
      - "traefik.http.routers.covet.tls.certresolver=letsencrypt"
      - "traefik.http.services.covet.loadbalancer.server.port=8000"
    environment:
      COVET_PUBLIC_URL: https://covet.example.com
      COVET_BEHIND_PROXY: "true"
      COVET_ALLOWED_HOSTS: covet.example.com

networks:
  proxy:
    external: true
```

If you use Traefik's `forwardAuth` middleware (e.g. pointed at
Authentik or Authelia), Covet's own OIDC auth still applies — the two
layers are independent. Using the Traefik forwardAuth + `COVET_OIDC_*`
together lets Traefik enforce network-level auth while Covet manages
collection ACL and sessions inside.

### nginx

```nginx
server {
    listen 443 ssl;
    server_name covet.example.com;

    ssl_certificate     /etc/letsencrypt/live/covet.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/covet.example.com/privkey.pem;

    client_max_body_size 50M;   # match COVET_DOCUMENTS_MAX_BYTES

    location / {
        proxy_pass         http://covet:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_set_header   Connection        "";
    }
}

server {
    listen 80;
    server_name covet.example.com;
    return 301 https://$host$request_uri;
}
```

Pair with [Certbot](https://certbot.eff.org/) or
[acme.sh](https://acme.sh/) for certificate management.

---



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
   Admins can pin trust status via `PATCH /metadata/registry/{entry_id}/trust`.
- Wanted-item tracking (`wanted` boolean on items) plus
   `GET /items?wanted=true/false` filtering and inline Wanted/Owned toggles in web
   with acquisition-date / purchase-price capture when marking owned.
- Bulk item actions via `POST /items/bulk-patch`, `POST /items/bulk-archive`,
   `POST /items/bulk-restore`, and `POST /items/bulk-delete`, with
   collection-scoped item-id validation and editor/owner role enforcement.
- CSV hierarchy round-trip via `GET /imports/csv/export` plus CSV import
   mapping targets `category_slug`, `ref:item_ref`, and `ref:parent_ref`
   to preserve parent/child links.
- Archive/disposition endpoints `POST /items/{id}/archive` and
   `POST /items/{id}/restore`, with `GET /items?include_archived=true`
   and `archived=true/false` filtering for archive views.
- Expanded item search across title/subtitle/notes/custom fields/identifiers,
   plus web `/` keyboard focus shortcut for collection search.
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

Attachment search indexes document text. PDF/text extraction works out
of the box; image OCR indexing requires the `tesseract` binary to be
installed in the runtime environment.

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
