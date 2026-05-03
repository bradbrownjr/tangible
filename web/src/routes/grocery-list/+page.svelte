<script lang="ts">
    import { onMount } from 'svelte';
    import { api, type Collection } from '$lib/api';
    import GroceryStoreManager from '$lib/GroceryStoreManager.svelte';
    import { GROCERY_CATEGORIES } from '$lib/groceryCategories';
    import { _ } from 'svelte-i18n';

    interface FeedEntry {
        id: string;
        source: { kind: 'ad_hoc' | 'depleted_item'; item_id: string | null };
        collection_id: string;
        name: string;
        subtitle: string | null;
        quantity: number;
        unit: string | null;
        notes: string | null;
        category_slug: string | null;
        linked_item_id: string | null;
        purchased_at: string | null;
        created_at: string;
    }

    function categoryLabel(slug: string | null): string {
        if (!slug) return '';
        const preset = GROCERY_CATEGORIES.find((c) => c.slug === slug);
        return preset && preset.slug !== 'custom' ? preset.label : slug;
    }

    let feed = $state<FeedEntry[]>([]);
    let collections = $state<Map<string, Collection>>(new Map());
    let hasPantry = $state(false);
    let loading = $state(true);
    let creatingPantry = $state(false);
    let error = $state('');

    let newCollectionId = $state('');
    let newName = $state('');
    let newCategorySlug = $state('');
    let customCategory = $state('');
    let newQuantity = $state(1);
    let newUnit = $state('');
    let newNotes = $state('');
    let adding = $state(false);

    let showStoreManager = $state(false);

    async function load() {
        loading = true;
        try {
            const [fetched, fetchedCollections] = await Promise.all([
                api.get<FeedEntry[]>('/grocery'),
                api.get<Collection[]>('/collections'),
            ]);
            feed = fetched;
            collections = new Map(fetchedCollections.map((c) => [c.id, c]));
            const pantry = fetchedCollections.find((c) => c.name.toLowerCase() === 'pantry');
            hasPantry = !!pantry;
            if (!newCollectionId) {
                newCollectionId = pantry?.id ?? (fetchedCollections[0]?.id ?? '');
            }
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function createPantry() {
        creatingPantry = true;
        try {
            const created = await api.post<Collection>('/collections', {
                name: 'Pantry',
                description: 'Grocery and pantry items',
            });
            hasPantry = true;
            collections.set(created.id, created);
            newCollectionId = created.id;
        } catch (err) {
            error = (err as Error).message;
        } finally {
            creatingPantry = false;
        }
    }

    async function addItem(e: SubmitEvent) {
        e.preventDefault();
        if (!newName.trim()) return;
        // If no collection exists yet, auto-create Pantry first
        if (!newCollectionId) {
            await createPantry();
            if (!newCollectionId) return;
        }
        const resolvedSlug =
            newCategorySlug === 'custom'
                ? (customCategory.trim().toLowerCase().replace(/\s+/g, '-') || null)
                : (newCategorySlug || null);
        adding = true;
        try {
            await api.post('/grocery', {
                collection_id: newCollectionId,
                name: newName.trim(),
                quantity: Math.max(1, newQuantity || 1),
                unit: newUnit.trim() || null,
                notes: newNotes.trim() || null,
                category_slug: resolvedSlug,
            });
            newName = '';
            newQuantity = 1;
            newUnit = '';
            newNotes = '';
            // keep category + collection — user is likely adding multiple items in the same section
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            adding = false;
        }
    }

    async function markPurchased(entry: FeedEntry) {
        try {
            if (entry.source.kind === 'ad_hoc') {
                await api.post(`/grocery/${entry.id}/purchase`, {
                    purchased_at: new Date().toISOString(),
                });
            } else if (entry.linked_item_id) {
                await api.post(`/items/${entry.linked_item_id}/restock`, {
                    quantity: 1,
                    purchased_at: new Date().toISOString(),
                });
            }
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    async function removeItem(entry: FeedEntry) {
        if (entry.source.kind !== 'ad_hoc') return;
        try {
            await api.delete(`/grocery/${entry.id}`);
            feed = feed.filter((e) => e.id !== entry.id);
        } catch (err) {
            error = (err as Error).message;
        }
    }

    onMount(load);
</script>

<div class="page-heading">
    <h1>{$_('grocery.title')}</h1>
    <button type="button" class="store-mgr-btn" title={$_('grocery.manage_stores_title')} onclick={() => { showStoreManager = true; }}>🏪 {$_('grocery.manage_stores_title')}</button>
</div>
<p class="muted">{$_('grocery.description')}</p>

{#if showStoreManager}
    <GroceryStoreManager onClose={() => { showStoreManager = false; }} />
{/if}

{#if !loading && !hasPantry}
    <div class="pantry-notice">
        {$_('grocery.no_pantry')}
        <button type="button" class="inline-btn" onclick={createPantry} disabled={creatingPantry}>
            {creatingPantry ? $_('grocery.creating_button') : $_('grocery.create_pantry_button')}
        </button>
    </div>
{/if}

<form class="add-form" onsubmit={addItem}>
    <div class="add-row-main">
        <input class="name-input" type="text" bind:value={newName} placeholder={$_('grocery.item_name_placeholder')} required />
        <select class="category-select" bind:value={newCategorySlug}>
            <option value="">{$_('grocery.no_category')}</option>
            {#each GROCERY_CATEGORIES as cat (cat.slug)}
                <option value={cat.slug}>{cat.label}</option>
            {/each}
            <option value="custom">{$_('grocery.custom_option')}</option>
        </select>
        {#if newCategorySlug === 'custom'}
            <input type="text" bind:value={customCategory} placeholder={$_('grocery.custom_placeholder')} class="custom-cat" />
        {/if}
    </div>
    <div class="add-row-details">
        <input type="number" min="1" bind:value={newQuantity} class="qty" />
        <input type="text" bind:value={newUnit} placeholder={$_('grocery.unit_placeholder')} class="unit" />
        <input type="text" bind:value={newNotes} placeholder={$_('grocery.notes_placeholder')} class="notes" />
        {#if collections.size > 1}
            <select bind:value={newCollectionId} class="collection-select">
                {#each [...collections.values()] as c (c.id)}
                    <option value={c.id}>{c.name}</option>
                {/each}
            </select>
        {/if}
        <button type="submit" disabled={adding || !newName.trim()}>{adding ? $_('grocery.adding_button') : $_('grocery.add_button')}</button>
    </div>
</form>

{#if loading}
    <p class="muted">{$_('common.loading')}</p>
{:else if error}
    <p class="error">{error}</p>
{:else if feed.length === 0}
    <p class="muted">{$_('grocery.empty')}</p>
{:else}
    <table>
        <thead>
            <tr>
                <th>{$_('grocery.col_item')}</th>
                <th>{$_('grocery.col_category')}</th>
                <th>{$_('grocery.col_qty')}</th>
                <th>{$_('grocery.col_collection')}</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            {#each feed as entry (entry.id)}
                <tr>
                    <td>
                        <strong>{entry.name}</strong>
                        {#if entry.subtitle}<span class="muted"> · {entry.subtitle}</span>{/if}
                        {#if entry.notes}<div class="muted small">{entry.notes}</div>{/if}
                        {#if entry.source.kind === 'depleted_item'}
                            <span class="badge-depleted">{$_('grocery.source_depleted')}</span>
                        {/if}
                    </td>
                    <td>
                        {#if entry.category_slug}
                            <span class="cat-chip">{categoryLabel(entry.category_slug)}</span>
                        {/if}
                    </td>
                    <td>{entry.quantity}{entry.unit ? '\u00a0' + entry.unit : ''}</td>
                    <td>
                        <a href="/collections/{entry.collection_id}">
                            {collections.get(entry.collection_id)?.name ?? entry.collection_id}
                        </a>
                    </td>
                    <td class="actions">
                        <button type="button" onclick={() => markPurchased(entry)}>
                            {$_('grocery.mark_purchased_button')}
                        </button>
                        {#if entry.source.kind === 'ad_hoc'}
                            <button type="button" class="secondary" onclick={() => removeItem(entry)}>
                                {$_('grocery.remove_button')}
                            </button>
                        {/if}
                    </td>
                </tr>
            {/each}
        </tbody>
    </table>
{/if}

<style>
    .page-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem; }
    .page-heading h1 { margin: 0; }
    .store-mgr-btn {
        background: none; border: 1px solid var(--border, #334); border-radius: 6px;
        padding: 0.35rem 0.75rem; font-size: 0.85rem; cursor: pointer; color: var(--text, #f1f5f9);
    }
    .store-mgr-btn:hover { border-color: var(--accent, #3b82f6); color: var(--accent, #3b82f6); }
    .pantry-notice {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.6rem 1rem;
        border-radius: 6px;
        background: var(--surface-alt, #1e2a3a);
        border: 1px solid var(--border, #334);
        margin-bottom: 1rem;
        font-size: 0.875rem;
        color: var(--muted, #94a3b8);
    }
    .inline-btn {
        background: var(--accent, #3b82f6);
        color: #fff;
        border: none;
        border-radius: 4px;
        padding: 0.25rem 0.75rem;
        font-size: 0.8rem;
        cursor: pointer;
    }
    .inline-btn:disabled { opacity: 0.6; cursor: default; }

    .add-form { margin: 1rem 0 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
    .add-row-main { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .add-row-details { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
    .name-input { flex: 2; min-width: 12rem; }
    .category-select { flex: 1; min-width: 10rem; }
    .custom-cat { flex: 1; min-width: 9rem; }
    .collection-select { min-width: 9rem; }
    input.qty { width: 4rem; }
    input.unit { width: 6rem; }
    input.notes { flex: 1; min-width: 12rem; }

    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 0.5rem; border-bottom: 1px solid var(--border, #e5e7eb); text-align: left; }
    .small { font-size: 0.85rem; }
    .actions { white-space: nowrap; display: flex; gap: 0.4rem; }
    .cat-chip {
        display: inline-block;
        font-size: 0.75rem;
        padding: 0.15rem 0.5rem;
        border-radius: 99px;
        background: var(--surface-alt, #1e2a3a);
        border: 1px solid var(--border, #334);
        color: var(--muted, #94a3b8);
        white-space: nowrap;
    }
    .badge-depleted {
        display: inline-block;
        font-size: 0.7rem;
        padding: 0.1rem 0.4rem;
        border-radius: 99px;
        background: #7c2d12;
        color: #fed7aa;
        margin-left: 0.25rem;
    }
</style>
