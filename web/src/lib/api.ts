/**
 * Minimal typed API client for the Covet server.
 *
 * Pages call `api.get('/items?...')` or `api.post('/auth/login', {...})`.
 * Errors are normalised to `ApiError` with the original status + body.
 */

export class ApiError extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown, message: string) {
        super(message);
        this.status = status;
        this.body = body;
    }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
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
        const message =
            (parsed && typeof parsed === 'object' && 'detail' in parsed
                ? String((parsed as { detail: unknown }).detail)
                : res.statusText) || `HTTP ${res.status}`;
        throw new ApiError(res.status, parsed, message);
    }
    return parsed as T;
}

export const api = {
    get: <T>(path: string) => request<T>('GET', path),
    post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
    patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
    put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
    delete: <T>(path: string) => request<T>('DELETE', path)
};

// --- Domain types (mirror server schemas) --------------------------------

export interface User {
    id: string;
    username: string;
    email: string | null;
    display_name: string | null;
    is_admin: boolean;
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
    location: string | null;
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
}

export interface Tag {
    id: string;
    name: string;
    color: string | null;
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
    created_by: string | null;
    created_at: string;
    updated_at: string;
}

export interface PublicConfig {
    version: string;
    public_url: string;
    registration_enabled: boolean;
    setup_required: boolean;
    oidc_enabled: boolean;
    oidc_providers: { name: string; label: string; login_url: string }[];
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
