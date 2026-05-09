/**
 * Minimal typed API client for the Tangible server.
 *
 * Pages call `api.get('/items?...')` or `api.post('/auth/login', {...})`.
 * Errors are normalised to `ApiError` with the original status + body.
 *
 * Set `silent: true` on individual calls to suppress automatic toast
 * notifications (e.g. background polls, login where the page shows its own
 * error display).
 */

import { showError, showToast } from './toast';

export class ApiError extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown, message: string) {
        super(message);
        this.status = status;
        this.body = body;
    }
}

// When a 502/503/504 is received, retry with backoff up to this many times
// before surfacing the error to the user. This smooths over rolling restarts.
const GATEWAY_STATUSES = new Set([502, 503, 504]);
const GATEWAY_MAX_RETRIES = 3;
const GATEWAY_RETRY_DELAY_MS = 2500;

async function requestWithRetry<T>(
    method: string,
    path: string,
    body: unknown,
    silent: boolean,
    attempt: number,
): Promise<T> {
    const init: RequestInit = {
        method,
        credentials: 'include',
        headers: { Accept: 'application/json' }
    };
    if (body !== undefined) {
        (init.headers as Record<string, string>)['Content-Type'] = 'application/json';
        init.body = JSON.stringify(body);
    }
    const res = await fetch('/api' + path, init);
    let parsed: unknown = null;
    const text = await res.text();
    if (text) {
        try {
            parsed = JSON.parse(text);
        } catch {
            parsed = text;
        }
    }
    if (!res.ok) {
        // Gateway errors during a server restart — retry silently with a
        // "server restarting" warning, then surface as error only if all
        // retries are exhausted.
        if (GATEWAY_STATUSES.has(res.status)) {
            if (attempt < GATEWAY_MAX_RETRIES) {
                if (attempt === 0 && !silent) {
                    showToast('Server is restarting — retrying…', 'warning', GATEWAY_RETRY_DELAY_MS * GATEWAY_MAX_RETRIES);
                }
                await new Promise((r) => setTimeout(r, GATEWAY_RETRY_DELAY_MS));
                return requestWithRetry<T>(method, path, body, silent, attempt + 1);
            }
        }
        const message =
            (parsed && typeof parsed === 'object' && 'detail' in parsed
                ? String((parsed as { detail: unknown }).detail)
                : res.statusText) || `HTTP ${res.status}`;
        const err = new ApiError(res.status, parsed, message);
        // Surface error as a toast unless the caller opted out or it's a
        // 401/403 (handled by the auth layer / page-level error display).
        if (!silent && res.status !== 401 && res.status !== 403) {
            showError(message);
        }
        throw err;
    }
    return parsed as T;
}

async function request<T>(method: string, path: string, body?: unknown, silent = false): Promise<T> {
    return requestWithRetry<T>(method, path, body, silent, 0);
}

export const api = {
    get: <T>(path: string, silent = false) => request<T>('GET', path, undefined, silent),
    post: <T>(path: string, body?: unknown, silent = false) => request<T>('POST', path, body, silent),
    patch: <T>(path: string, body?: unknown, silent = false) => request<T>('PATCH', path, body, silent),
    put: <T>(path: string, body?: unknown, silent = false) => request<T>('PUT', path, body, silent),
    delete: <T>(path: string, silent = false) => request<T>('DELETE', path, undefined, silent),
    upload: async <T>(path: string, formData: FormData, silent = false): Promise<T> => {
        const res = await fetch('/api' + path, {
            method: 'POST',
            credentials: 'include',
            headers: { Accept: 'application/json' },
            body: formData
        });
        const text = await res.text();
        let parsed: unknown = null;
        if (text) {
            try { parsed = JSON.parse(text); } catch { parsed = text; }
        }
        if (!res.ok) {
            const message =
                (parsed && typeof parsed === 'object' && 'detail' in parsed
                    ? String((parsed as { detail: unknown }).detail)
                    : res.statusText) || `HTTP ${res.status}`;
            if (!silent && res.status !== 401 && res.status !== 403) {
                showError(message);
            }
            throw new ApiError(res.status, parsed, message);
        }
        return parsed as T;
    }
};

// --- Domain types (mirror server schemas) --------------------------------

export interface User {
    id: string;
    username: string;
    email: string | null;
    display_name: string | null;
    locale?: string | null;
    is_admin: boolean;
    enrollment_required?: boolean;
}

/** Display label for a user: full name when set, else username. */
export function userLabel(u: { display_name?: string | null; username: string }): string {
    return (u.display_name && u.display_name.trim()) || u.username;
}

export interface Collection {
    id: string;
    name: string;
    description: string | null;
    icon: string | null;
    is_public: boolean;
    owner_id: string;
    default_category_slug: string | null;
    my_role: Role | null;
}

export interface Category {
    id: string;
    parent_id: string | null;
    slug: string;
    name: string;
    description: string | null;
    position: number;
    is_system: boolean;
    is_active: boolean;
}

export interface CategoryNode {
    id: string;
    slug: string;
    name: string;
    description: string | null;
    children: CategoryNode[];
}

export interface Item {
    id: string;
    collection_id: string;
    category_id: string;
    category_slug: string | null;
    title: string;
    subtitle: string | null;
    notes: string | null;
    condition: string | null;
    quantity: number;
    purchase_price: number | null;
    current_value: number | null;
    rollup_current_value: number | null;
    currency: string | null;
    location_id: string | null;
    location_path: string[] | null;
    identifiers: Record<string, unknown>;
    attrs: Record<string, unknown>;
    template_id: string | null;
    depleted: boolean;
    wanted: boolean;
    archived_at: string | null;
    disposition_type: string | null;
    disposition_at: string | null;
    disposition_amount: number | null;
    disposition_buyer: string | null;
    disposition_note: string | null;
    flagged_note: string | null;
    flagged_at: string | null;
    purchased_at: string | null;
    use_by_date: string | null;
    date_frozen: string | null;
    date_opened: string | null;
    list_type: string | null;
    tag_names: string[];
}

export interface Tag {
    id: string;
    name: string;
    color: string | null;
}

export interface Contact {
    id: string;
    owner_id: string;
    name: string;
    email: string | null;
    phone: string | null;
    notes: string | null;
}

export type Role = 'viewer' | 'editor' | 'owner';

export interface Membership {
    id: string;
    collection_id: string;
    user_id: string;
    role: Role;
    username: string;
    email: string | null;
    display_name: string | null;
}

export interface ShareLink {
    id: string;
    collection_id: string;
    slug: string;
    label: string | null;
    expires_at: string | null;
    revoked: boolean;
    created_at: string;
}

export interface Invitation {
    id: string;
    collection_id: string;
    role: string;
    email: string | null;
    expires_at: string | null;
    accepted_at: string | null;
    created_at: string;
}

export interface InvitationCreated extends Invitation {
    token: string;
}

export interface InvitationPreview {
    collection_id: string;
    collection_name: string;
    role: string;
    email: string | null;
    expires_at: string | null;
}

export type LocationKind = 'home' | 'floor' | 'room' | 'zone' | 'container';

export interface LocationNode {
    id: string;
    collection_id: string;
    name: string;
    kind: LocationKind;
    parent_id: string | null;
    notes: string | null;
    qr_slug: string | null;
    item_count: number;
    children: LocationNode[];
}

export type BundleAssetKind = 'manual' | 'diagram' | 'firmware' | 'service' | 'parts' | 'other';

export interface BundleAsset {
    id: string;
    bundle_id: string;
    sha256: string;
    mime_type: string;
    byte_size: number;
    filename: string;
    label: string | null;
    kind: BundleAssetKind;
    sort_order: number;
    created_at: string;
    updated_at: string;
}

export interface ManualBundle {
    id: string;
    collection_id: string;
    title: string;
    description: string | null;
    primary_asset_id: string | null;
    created_at: string;
    updated_at: string;
    assets: BundleAsset[];
    item_ids: string[];
}

export interface AuditLogEntry {
    id: string;
    actor_user_id: string | null;
    collection_id: string | null;
    action: string;
    target_type: string | null;
    target_id: string | null;
    payload: Record<string, unknown> | null;
    created_at: string;
}

export type TemplateFieldType =
    | 'text'
    | 'number'
    | 'boolean'
    | 'date'
    | 'url'
    | 'select'
    | 'multi_value'
    | 'relation';
export type TemplateSelectSource = 'static' | 'dynamic';
export type TemplateRelationScope = 'same_collection' | 'any_collection';

export interface TemplateField {
    key: string;
    label: string;
    type: TemplateFieldType;
    select_source?: TemplateSelectSource;
    relation_scope?: TemplateRelationScope;
    required?: boolean;
    default?: unknown;
    options?: string[] | null;
    help?: string | null;
}

export interface ItemTemplate {
    id: string;
    collection_id: string;
    name: string;
    category_slug: string;
    description: string | null;
    fields: TemplateField[];
    scraper_id: string | null;
    created_by: string | null;
    created_at: string;
    updated_at: string;
}

export interface ScaffoldTemplate {
    name: string;
    category_slug: string;
    fields: TemplateField[];
}

export interface PublicConfig {
    version: string;
    public_url: string;
    registration_enabled: boolean;
    setup_required: boolean;
    oidc_enabled: boolean;
    oidc_providers: { name: string; label: string; login_url: string }[];
    require_2fa: boolean;
}

export interface SiteSetting {
    key: string;
    value: string | null;
    is_set: boolean;
    source: 'database' | 'environment' | 'default';
    type: 'bool' | 'int' | 'str';
    description: string;
    sensitive: boolean;
    section: string;
    env_var: string | null;
}

export interface ScraperRegistryEntry {
    id: string;
    name: string;
    provider: string;
    description: string;
    category_slug: string;
    homepage: string;
    trusted: boolean;
    fields: Array<Record<string, unknown>>;
}

// --- Phase 12 types -------------------------------------------------------

export interface MaintenanceTask {
    id: string;
    item_id: string;
    name: string;
    notes: string | null;
    interval_days: number | null;
    last_completed_at: string | null;
    next_due_at: string | null;
    created_at: string;
    updated_at: string;
}

export interface MaintenanceCompletion {
    id: string;
    task_id: string;
    completed_at: string;
    notes: string | null;
    cost: string | null;
    currency: string | null;
    technician: string | null;
    odometer_reading: string | null;
    hours_reading: string | null;
}

export interface Chore {
    id: string;
    collection_id: string;
    name: string;
    notes: string | null;
    interval_days: number | null;
    last_completed_at: string | null;
    next_due_at: string | null;
    created_at: string;
    updated_at: string;
}

export interface ChoreCompletion {
    id: string;
    chore_id: string;
    completed_at: string;
    notes: string | null;
    cost: string | null;
    currency: string | null;
    technician: string | null;
}

export interface DueAlert {
    id: string;
    kind: string;
    severity: 'warning' | 'critical';
    title: string;
    collection_id: string;
    item_id: string | null;
    lot_id: string | null;
    due_at: string | null;
    details: string | null;
}

export interface StandaloneTask {
    id: string;
    collection_id: string;
    item_id: string | null;
    title: string;
    notes: string | null;
    due_at: string | null;
    completed_at: string | null;
    completed_by_user_id: string | null;
    assigned_to_user_id: string | null;
    created_by_user_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface ScoreboardEntry {
    user_id: string;
    display_name: string;
    chore_count: number;
    maintenance_count: number;
    task_count: number;
    total: number;
    achievements: string[];
}

export interface CommentAuthor {
    id: string;
    username: string;
    display_name: string | null;
}

export interface ItemComment {
    id: string;
    item_id: string;
    parent_id: string | null;
    body: string;
    created_at: string;
    updated_at: string;
    author: CommentAuthor;
    reply_count: number;
}
