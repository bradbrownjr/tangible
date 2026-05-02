# Admin guide

Operating Tangible for one or more users: first-run setup, accounts,
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
  - [Required Tangible env vars (all proxies)](#required-tangible-env-vars-all-proxies)
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
   (unless `TANGIBLE_DB_AUTO_MIGRATE=false`).
2. If `TANGIBLE_ADMIN_USERNAME` **and** `TANGIBLE_ADMIN_PASSWORD` are set in
   the environment, that admin account is created automatically. Pair
   with `TANGIBLE_ADMIN_PASSWORD_FILE` for Docker secrets / Unraid file
   mounts.
3. Otherwise, browse to the URL and click **Register**. The very first
   user to sign up is automatically promoted to admin — even when
   `TANGIBLE_REGISTRATION_ENABLED=false`. After that initial signup, the
   normal `TANGIBLE_REGISTRATION_ENABLED` rule applies and further public
   registration is rejected with HTTP 403 unless you explicitly enable
   it.

Once an admin exists, self-registration is **off** by default. Set
`TANGIBLE_REGISTRATION_ENABLED=true` to allow open signup, or invite users
individually (see below).

## Users and roles

Tangible has two layers of authorization:

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
docker exec -it tangible tangible bootstrap-admin   # only re-creates if missing
```

For other users, use the admin UI's **Reset password** action, which
sets a one-time password the user must change on next login.

### Disabling / removing a user

Disable from the admin UI to keep their content (loans, audit trail)
intact. Deleting a user transfers ownership of their collections to
the deleting admin and removes their sessions and tokens.

## SSO / OIDC

Tangible speaks OpenID Connect via Authlib. Multiple providers can be
enabled simultaneously (e.g. Authentik *and* Google). Set
`TANGIBLE_OIDC_ENABLED=true` to activate the system, then configure one
or more providers as shown below.

Common env vars that apply to all providers:

| Variable | Default | Notes |
|---|---|---|
| `TANGIBLE_OIDC_ENABLED` | `false` | Master switch |
| `TANGIBLE_OIDC_AUTO_CREATE_USERS` | `true` | Create local account on first login |
| `TANGIBLE_OIDC_DEFAULT_ROLE` | `user` | Role for auto-created users (`user` or `admin`) |

### Authentik

Create an OAuth2/OIDC provider in Authentik. Set the redirect URI to
`https://tangible.example.com/auth/oidc/authentik/callback`.

```env
TANGIBLE_OIDC_AUTHENTIK_DISPLAY_NAME=Authentik
TANGIBLE_OIDC_AUTHENTIK_ISSUER=https://auth.example.com/application/o/tangible/
TANGIBLE_OIDC_AUTHENTIK_CLIENT_ID=tangible
TANGIBLE_OIDC_AUTHENTIK_CLIENT_SECRET_FILE=/run/secrets/authentik_secret
TANGIBLE_OIDC_AUTHENTIK_ADMIN_GROUPS=tangible-admins
```

`ADMIN_GROUPS` (comma-separated group claims) auto-promotes anyone in
those groups to global admin. If not set, all OIDC users get
`TANGIBLE_OIDC_DEFAULT_ROLE`.

### Keycloak

Create a client in your Keycloak realm. Set **Access Type** to
`confidential` and add the redirect URI
`https://tangible.example.com/auth/oidc/keycloak/callback`.

```env
TANGIBLE_OIDC_KEYCLOAK_DISPLAY_NAME=Keycloak
TANGIBLE_OIDC_KEYCLOAK_ISSUER=https://keycloak.example.com/realms/myrealm
TANGIBLE_OIDC_KEYCLOAK_CLIENT_ID=tangible
TANGIBLE_OIDC_KEYCLOAK_CLIENT_SECRET_FILE=/run/secrets/keycloak_secret
TANGIBLE_OIDC_KEYCLOAK_ADMIN_GROUPS=tangible-admins
```

Keycloak issues group claims as `/group-name` paths by default. The
admin-group check is a substring match, so `tangible-admins` matches
`/tangible-admins`.

### Authelia

Authelia acts as an OIDC provider from version 4.38+. Create a client
entry in `configuration.yml` and register the redirect URI
`https://tangible.example.com/auth/oidc/authelia/callback`.

```yaml
# authelia configuration.yml excerpt
identity_providers:
  oidc:
    clients:
      - id: tangible
        description: Tangible
        secret: '$pbkdf2-sha512$...'   # bcrypt or pbkdf2 hash of the secret
        redirect_uris:
          - https://tangible.example.com/auth/oidc/authelia/callback
        scopes: [openid, profile, email, groups]
        grant_types: [authorization_code]
```

```env
TANGIBLE_OIDC_AUTHELIA_DISPLAY_NAME=Authelia
TANGIBLE_OIDC_AUTHELIA_ISSUER=https://authelia.example.com
TANGIBLE_OIDC_AUTHELIA_CLIENT_ID=tangible
TANGIBLE_OIDC_AUTHELIA_CLIENT_SECRET_FILE=/run/secrets/authelia_secret
TANGIBLE_OIDC_AUTHELIA_ADMIN_GROUPS=tangible-admins
```

### Google / GitHub (external OAuth)

For households that use Google or GitHub accounts, set the redirect URI
in the provider's developer console to
`https://tangible.example.com/auth/oidc/<provider>/callback`.

```env
# Google
TANGIBLE_OIDC_GOOGLE_DISPLAY_NAME=Google
TANGIBLE_OIDC_GOOGLE_ISSUER=https://accounts.google.com
TANGIBLE_OIDC_GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
TANGIBLE_OIDC_GOOGLE_CLIENT_SECRET_FILE=/run/secrets/google_secret

# GitHub
TANGIBLE_OIDC_GITHUB_DISPLAY_NAME=GitHub
TANGIBLE_OIDC_GITHUB_ISSUER=https://token.actions.githubusercontent.com
TANGIBLE_OIDC_GITHUB_CLIENT_ID=Ov23li...
TANGIBLE_OIDC_GITHUB_CLIENT_SECRET_FILE=/run/secrets/github_secret
```

GitHub does not issue an `email` scope by default — enable it in the
OAuth app settings or users will need to set a local email after first
login.

See the [Configuration reference](configuration.md#oidc--oauth-optional)
for every per-provider setting.

---

## Reverse proxy setup

Most self-hosters already run a reverse proxy. Tangible sits behind it
on port 8000. All proxies must:

- Forward the real client IP via `X-Forwarded-For`.
- Pass `Host`, `X-Forwarded-Proto`, and `X-Real-IP` headers.
- Terminate TLS (Tangible does not manage certificates).

### Required Tangible env vars (all proxies)

Set these regardless of which proxy you use:

```env
TANGIBLE_PUBLIC_URL=https://tangible.example.com
TANGIBLE_BEHIND_PROXY=true
TANGIBLE_ALLOWED_HOSTS=tangible.example.com
```

Without `TANGIBLE_BEHIND_PROXY=true`, Tangible ignores forwarded-IP headers
and will rate-limit your proxy's IP instead of the real clients'.
Without `TANGIBLE_ALLOWED_HOSTS`, the host-header allowlist will reject
requests for your domain with HTTP 400.

### Caddy

Caddy obtains and renews TLS automatically via Let's Encrypt or ZeroSSL.

```caddy
tangible.example.com {
    encode zstd gzip
    reverse_proxy tangible:8000
}
```

Place this in your `Caddyfile` (global or per-site). Tangible and Caddy
must share a Docker network. A full reference snippet is also included at
[`docker/Caddyfile.example`](../docker/Caddyfile.example).

If you need the WebSocket upgrade header for future SSE support:

```caddy
tangible.example.com {
    encode zstd gzip
    reverse_proxy tangible:8000 {
        header_up Connection {>Connection}
        header_up Upgrade {>Upgrade}
    }
}
```

### Traefik

Add Traefik labels to the Tangible service in your Compose file. This
assumes a Traefik instance already running with a `proxy` external
network and an `https` entrypoint:

```yaml
services:
  tangible:
    image: ghcr.io/bradbrownjr/tangible:0
    networks:
      - proxy
      - default
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tangible.rule=Host(`tangible.example.com`)"
      - "traefik.http.routers.tangible.entrypoints=https"
      - "traefik.http.routers.tangible.tls.certresolver=letsencrypt"
      - "traefik.http.services.tangible.loadbalancer.server.port=8000"
    environment:
      TANGIBLE_PUBLIC_URL: https://tangible.example.com
      TANGIBLE_BEHIND_PROXY: "true"
      TANGIBLE_ALLOWED_HOSTS: tangible.example.com

networks:
  proxy:
    external: true
```

If you use Traefik's `forwardAuth` middleware (e.g. pointed at
Authentik or Authelia), Tangible's own OIDC auth still applies — the two
layers are independent. Using the Traefik forwardAuth + `TANGIBLE_OIDC_*`
together lets Traefik enforce network-level auth while Tangible manages
collection ACL and sessions inside.

### nginx

```nginx
server {
    listen 443 ssl;
    server_name tangible.example.com;

    ssl_certificate     /etc/letsencrypt/live/tangible.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tangible.example.com/privkey.pem;

    client_max_body_size 50M;   # match TANGIBLE_DOCUMENTS_MAX_BYTES

    location / {
        proxy_pass         http://tangible:8000;
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
    server_name tangible.example.com;
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
docker exec tangible tangible backup alice - > alice-2026-04-29.json
```

Restore into the same or a different deployment:

```bash
docker exec -i tangible tangible restore alice - < alice-2026-04-29.json
```

### Volume snapshots (recommended)

For full fidelity (photos, documents, sync state), snapshot the
volumes:

```bash
# Stop the container so SQLite is consistent (skip if using Postgres).
docker compose stop tangible

tar czf tangible-data-$(date +%F).tgz \
    -C /var/lib/docker/volumes/tangible_data/_data . \
    -C /var/lib/docker/volumes/tangible_config/_data .

docker compose start tangible
```

Or use [`restic`](https://restic.net/) with hooks. With Postgres,
back up the database with `pg_dump` *and* the `/data` volume (which
still holds photos and documents).

### What to retain

| Path | Why |
|---|---|
| `/data/tangible.db` (+ `-wal`, `-shm`) | SQLite database |
| `/data/photos/` | Item photos (content-addressed) |
| `/data/documents/` | Item attachments (content-addressed) |
| `/config/secret.key` | Session & cookie signing key. Lose it → all sessions invalid; logged-in users sign back in. |
| `/config/tangible.yaml` / `tangible.env` | Optional declarative config |

## Upgrading

```bash
docker compose pull
docker compose up -d
```

The container runs `alembic upgrade head` on start unless
`TANGIBLE_DB_AUTO_MIGRATE=false`. Always:

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
  tangible:
    image: ghcr.io/bradbrownjr/tangible:0.11.0
```

### Rollback

If a migration goes badly:

1. Restore the volume snapshot taken before upgrade.
2. Re-deploy the previous image tag.
3. File a bug with the offending version + `docker logs tangible` output.

## Observability

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Liveness/readiness probe. Used by the container HEALTHCHECK. |
| `GET /readyz` | Same, with a database round-trip. |
| `GET /version` | `{"version": "X.Y.Z", "git_sha": "..."}`. |
| `GET /metrics` | Prometheus metrics: `tangible_http_requests_total`, latency histograms, sync queue depth. |

Logs use [structlog](https://www.structlog.org). For machine-parseable
output:

```env
TANGIBLE_LOG_FORMAT=json
TANGIBLE_LOG_LEVEL=INFO
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
| `TANGIBLE_RATE_LIMIT_LOGIN` | `5/minute` | Per-IP, login + register |
| `TANGIBLE_RATE_LIMIT_API` | `120/minute` | Per-token (or per-IP for unauth) |

Rate-limit hits return `429 Too Many Requests` with a
`Retry-After` header.

## Storage limits

Reject huge uploads early to protect the disk:

| Variable | Default |
|---|---|
| `TANGIBLE_PHOTOS_MAX_BYTES` | `26214400` (25 MiB) |
| `TANGIBLE_DOCUMENTS_MAX_BYTES` | `52428800` (50 MiB) |
| `TANGIBLE_PHOTOS_DIR` | `${TANGIBLE_DATA_DIR}/photos` |
| `TANGIBLE_DOCUMENTS_DIR` | `${TANGIBLE_DATA_DIR}/documents` |

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
docker exec tangible sqlite3 /data/tangible.db "VACUUM;"
```

### Rotate the session key

Replace `/config/secret.key` and restart. All sessions are invalidated;
API tokens continue to work.

### Force re-migration

```bash
docker exec tangible tangible migrate
```

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Container restarts in a loop | `docker logs tangible` — usually a bad `TANGIBLE_*` value or migration failure. |
| 400 Bad Request on every request | `TANGIBLE_ALLOWED_HOSTS` doesn't include the host you're hitting. Loopback (`localhost`, `127.0.0.1`, `::1`) is always allowed. |
| OIDC callback returns "invalid state" | Cookies blocked by reverse-proxy stripping `Set-Cookie`, or `TANGIBLE_FORCE_HTTPS` mismatch. |
| `Permission denied` writing `/data` | `PUID`/`PGID` don't match the host owner of the volume. Adjust env vars or `chown` the volume. |
| `429` storms during import | Bulk operations should use the CLI, not the API. Or raise `TANGIBLE_RATE_LIMIT_API`. |
| OIDC button missing | Provider env vars not set or `TANGIBLE_OIDC_ENABLED=false`. Check `docker exec tangible env | grep OIDC`. |
| Sync conflicts on mobile | Open the item; Tangible shows both versions and lets you pick. CRDT keeps history forever in `automerge_changes`. |

## Getting help

- File issues at <https://github.com/bradbrownjr/tangible/issues>.
- Include `docker exec tangible tangible version`, the relevant section of
  `docker logs tangible`, and your sanitized `tangible.env`.
