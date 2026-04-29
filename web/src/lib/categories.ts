/**
 * Category catalog (loaded once per session).
 *
 * The server ships a curated 2-level taxonomy under `GET /categories`. The
 * web client caches it in module state and exposes a few helpers used by
 * the item / template / import UIs to render cascading selects.
 */

import { api, type Category } from './api';

let cache: Category[] | null = null;
let inflight: Promise<Category[]> | null = null;

export async function loadCategories(force = false): Promise<Category[]> {
    if (cache && !force) return cache;
    if (inflight) return inflight;
    inflight = api
        .get<Category[]>('/categories')
        .then((rows) => {
            cache = rows;
            inflight = null;
            return rows;
        })
        .catch((err) => {
            inflight = null;
            throw err;
        });
    return inflight;
}

export function getCachedCategories(): Category[] {
    return cache ?? [];
}

export function rootCategories(rows: Category[]): Category[] {
    return rows.filter((c) => c.parent_id === null);
}

export function childrenOf(rows: Category[], parentId: string): Category[] {
    return rows.filter((c) => c.parent_id === parentId);
}

export function findBySlug(rows: Category[], slug: string): Category | undefined {
    return rows.find((c) => c.slug === slug);
}

export function rootForLeaf(rows: Category[], leafSlug: string): Category | undefined {
    const leaf = findBySlug(rows, leafSlug);
    if (!leaf) return undefined;
    if (leaf.parent_id === null) return leaf;
    return rows.find((c) => c.id === leaf.parent_id);
}
