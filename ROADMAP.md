# Covet Roadmap

This is a living plan, not a commitment. Order and scope shift as we learn.
For shipped work see [CHANGELOG.md](CHANGELOG.md). For agent rules see
[AGENTS.md](AGENTS.md).

Each phase groups changes that ship together as a coherent user story.
Within a phase, items are roughly ordered by leverage.

---

## Phase 8 — Make it shareable

Today Covet treats every user as an island. The biggest gap vs. comparable
self-hosted inventory tools is multi-user / shared collections. This phase
lands the auth + ACL plumbing once, then several user-visible features fall
out of it.

- **OIDC / OAuth2 SSO** — federate with Authelia, Authentik, Keycloak,
  Google, GitHub. Reuse the existing session machinery; add an
  `external_identity` table keyed by `(issuer, subject)`. Settings UI to
  link / unlink providers.
- **Collection ACL** — `(collection_id, user_id, role)` with roles
  `owner`, `editor`, `viewer`. Server enforces on every items / photos /
  loans / sync route. Web + Android UIs gain a "Members" panel and an
  invite-by-email-or-token flow.
- **Public read-only share links** — generate an unguessable URL for a
  collection (or a single item) that renders a stripped-down read-only
  view without auth. Per-link revoke.
- **Invitation tokens** — short-lived tokens for onboarding non-OIDC
  household members.
- **Audit log** — who changed what, when. Surface in collection settings.

## Phase 9 — Make items richer

Once items can be shared, the next pressure is making each item carry
more useful data without manual data entry.

- **Item templates / per-type custom fields** — define reusable schemas
  ("Book", "Board game", "Tool") with default fields, units, and
  validation. Items inherit from a template; templates are
  collection-scoped and exportable.
- **URL metadata scraper** — paste an Amazon / IGDB / IMDB / Discogs
  link, prefill title, cover image, and type-specific fields. Plug-in
  adapters per source so new sites are a small contribution.
- **Document attachments** — upload PDFs (receipts, manuals, warranties)
  alongside photos. Inline preview on web; download on Android.
- **Warranty / expiry tracking** — optional "expires on" on attachments
  and items; surfaces in a dashboard widget and triggers reminders.
- **Maintenance schedules** — recurring tasks per item ("change furnace
  filter every 90 days", "service car"). Reuses the loan reminder /
  notification path. Mark-complete records history.
- **Parent / child items (containers, kits)** — a "Toolbox" item can
  contain "Hammer", "Tape measure". Move container, contents move with
  it. Exports preserve hierarchy.
- **Multi-photo upload + add photo from URL** — pick many at once on
  web/Android, or paste an image URL. Re-order; pick primary.
- **HEIC support + EXIF rotation fix** — accept HEIC server-side,
  transcode on upload, honor EXIF orientation so iPhone photos aren't
  sideways.

## Phase 10 — Make it efficient

With more items per collection, bulk operations and discovery become the
bottleneck. This phase is about scaling the UX.

- **Bulk select + bulk actions** — multi-select on items list (web +
  Android) for bulk move, tag, delete, set-field, lend, archive.
- **Better search** — case-insensitive across locales, accent-folding,
  fuzzy matching, search across custom fields and attachments OCR text.
  Keyboard-driven palette on web (`/`).
- **Hierarchical / nested tags** — `electronics > audio > cables`. UI
  shows breadcrumbs; filters cascade.
- **QR code label sheets** — generate a printable PDF of QR labels for
  selected items. Android scanner gains a "find by QR" mode (vs.
  scan-to-create today) that jumps straight to item detail.
- **Wishlist / wanted items** — flag items the user doesn't own yet;
  one click converts to owned with acquisition date and price.
- **Reports** — per-collection totals (count, value), BoM PDF export,
  insurance-friendly export bundle (CSV + photos + PDFs in a zip).
- **CSV export with parent/child preserved** — round-trip the new item
  hierarchy through CSV without losing relationships.
- **Webhooks** — outbound HTTP on item events (created, updated,
  loaned, returned, maintenance-due) for Home Assistant, n8n, Discord.
- **i18n scaffold** — extract strings, wire Crowdin or Weblate, ship
  with English + a couple of community translations.

---

## Backlog (not yet phased)

Smaller items that don't slot cleanly into a phase yet:

- Duplicate item button.
- Drag-and-drop reorder of photos.
- Server-side thumbnail generation pipeline.
- Two-factor auth (TOTP) for local accounts.
- Account deletion / data export self-service.
- Compose example for traefik with Authentik.
- Native iOS app (long-term — Android first).

## Done

See [CHANGELOG.md](CHANGELOG.md) for what has shipped (auth, items,
collections, photos, tags, loans, importers, sync, web UI, Android app
with offline cache + sync worker, Docker image, CI).
