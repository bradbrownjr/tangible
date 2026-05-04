<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { api, type Collection } from '$lib/api';
    import ShoppingStoreManager from '$lib/ShoppingStoreManager.svelte';
    import { categoriesForType, GROCERY_CATEGORIES } from '$lib/shoppingCategories';
    import { _ } from 'svelte-i18n';

    const VALID_TYPES = ['groceries', 'hardware', 'home_goods', 'wish_list'] as const;
    type ListType = typeof VALID_TYPES[number];

    const BACKING_COLLECTION: Record<string, string> = {
        groceries:  'Pantry',
        hardware:   'Hardware',
        home_goods: 'Home Goods',
    };

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
        list_type: string;
        wish_url: string | null;
        wish_priority: number | null;
        linked_item_id: string | null;
        purchased_at: string | null;
        created_at: string;
    }

    let listType = $derived((page.params.type ?? 'groceries') as ListType);

    let categories = $derived(categoriesForType(listType));

    function typeTitle(t: string): string {
        switch (t) {
            case 'groceries':  return $_('lists.type.groceries');
            case 'hardware':   return $_('lists.type.hardware');
            case 'home_goods': return $_('lists.type.home_goods');
            case 'wish_list':  return $_('lists.type.wish_list');
            default:           return t;
        }
    }

    function categoryLabel(slug: string | null): string {
        if (!slug) return '';
        const preset = categories.find((c) => c.slug === slug);
        return preset ? preset.label : slug;
    }

    function priorityLabel(p: number | null): string {
        switch (p) {
            case 1: return $_('lists.priority.low');
            case 2: return $_('lists.priority.medium');
            case 3: return $_('lists.priority.high');
            default: return '';
        }
    }

    let feed = $state<FeedEntry[]>([]);
    let collections = $state<Map<string, Collection>>(new Map());
    let loading = $state(true);
    let error = $state('');

    let newCollectionId = $state('');
    let newName = $state('');
    let newCategorySlug = $state('');
    let customCategory = $state('');
    let newQuantity = $state(1);
    let newUnit = $state('');
    let newNotes = $state('');
    let newWishUrl = $state('');
    let newWishPriority = $state<number | ''>('');
    let adding = $state(false);

    let showStoreManager = $state(false);

    async function load() {
        loading = true;
        try {
            const [fetched, fetchedCollections] = await Promise.all([
                api.get<FeedEntry[]>(`/lists?list_type=${listType}`),
                api.get<Collection[]>('/collections'),
            ]);
            feed = fetched;
            collections = new Map(fetchedCollections.map((c) => [c.id, c]));
            const backingName = BACKING_COLLECTION[listType];
            const backing = backingName
                ? fetchedCollections.find((c) => c.name.toLowerCase() === backingName.toLowerCase())
                : null;
            if (!newCollectionId) {
                newCollectionId = backing?.id ?? (fetchedCollections[0]?.id ?? '');
            }
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function createBackingCollection() {
        const name = BACKING_COLLECTION[listType];
        if (!name) return;
        try {
            const created = await api.post<Collection>('/collections', {
                name,
                description: name + ' items',
            });
            collections.set(created.id, created);
            newCollectionId = created.id;
        } catch (err) {
            error = (err as Error).message;
        }
    }

    async function addItem(e: SubmitEvent) {
        e.preventDefault();
        if (!newName.trim()) return;
        if (!newCollectionId && listType !== 'wish_list') {
            await createBackingCollection();
            if (!newCollectionId) return;
        }
        const resolvedSlug =
            newCategorySlug === 'custom'
                ? (customCategory.trim().toLowerCase().replace(/\s+/g, '-') || null)
                : (newCategorySlug || null);
        adding = true;
        try {
            const body: Record<string, unknown> = {
                collection_id: newCollectionId || null,
                name: newName.trim(),
                quantity: Math.max(1, newQuantity || 1),
                unit: newUnit.trim() || null,
                notes: newNotes.trim() || null,
                category_slug: resolvedSlug,
                list_type: listType,
            };
            if (listType === 'wish_list') {
                body.wish_url = newWishUrl.trim() || null;
                body.wish_priority = newWishPriority || null;
            }
            await api.post('/lists', body);
            newName = '';
            newQuantity = 1;
            newUnit = '';
            newNotes = '';
            newWishUrl = '';
            newWishPriority = '';
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
                await api.post(`/lists/${entry.id}/purchase`, {
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
            await api.delete(`/lists/${entry.id}`);
            feed = feed.filter((e) => e.id !== entry.id);
        } catch (err) {
            error = (err as Error).message;
        }
    }

    // Reload when the route type param changes (user clicks another list in nav)
    $effect(() => {
        const _ = listType;
        newCollectionId = '';
        newCategorySlug = '';
        load();
    });

    onMount(() => {
        if (!VALID_TYPES.includes(listType as ListType)) {
            goto('/lists/groceries');
        }
    });
</script>

<div class="page-heading">
    <h1>{typeTitle(listType)}</h1>
    {#if listType === 'groceries'}
        <button type="button" class="store-mgr-btn" title={$_('grocery.manage_stores_title')} onclick={() => { showStoreManager = true; }}>
            🏪 {$_('grocery.manage_stores_title')}
        </button>
    {/if}
</div>
<p class="muted">{$_(`lists.description.${listType}`)}</p>

{#if showStoreManager}
    <ShoppingStoreManager onClose={() => { showStoreManager = false; }} />
{/if}

<form class="add-form" onsubmit={addItem}>
    <div class="add-row-main">
        <input class="name-input" type="text" bind:value={newName} placeholder={$_('lists.item_name_placeholder')} required />
        {#if listType !== 'wish_list'}
            <select class="category-select" bind:value={newCategorySlug}>
                <option value="">{$_('grocery.no_category')}</option>
                {#each categories as cat (cat.slug)}
                    <option value={cat.slug}>{cat.label}</option>
                {/each}
                <option value="custom">{$_('grocery.custom_option')}</option>
            </select>
            {#if newCategorySlug === 'custom'}
                <input type="text" bind:value={customCategory} placeholder={$_('grocery.custom_placeholder')} class="custom-cat" />
            {/if}
        {/if}
    </div>
    <div class="add-row-details">
        {#if listType !== 'wish_list'}
            <input type="number" min="1" bind:value={newQuantity} class="qty" />
            <input type="text" bind:value={newUnit} placeholder={$_('grocery.unit_placeholder')} class="unit" />
        {/if}
        <input type="text" bind:value={newNotes} placeholder={$_('grocery.notes_placeholder')} class="notes" />
        {#if listType === 'wish_list'}
            <input type="url" bind:value={newWishUrl} placeholder={$_('lists.wish_url_placeholder')} class="wish-url" />
            <select bind:value={newWishPriority} class="wish-priority">
                <option value="">{$_('lists.wish_priority_any')}</option>
                <option value={1}>{$_('lists.priority.low')}</option>
                <option value={2}>{$_('lists.priority.medium')}</option>
                <option value={3}>{$_('lists.priority.high')}</option>
            </select>
        {/if}
        {#if collections.size > 1 && listType !== 'wish_list'}
            <select bind:value={newCollectionId} class="collection-select">
                {#each [...collections.values()] as c (c.id)}
                    <option value={c.id}>{c.name}</option>
                {/each}
            </select>
        {/if}
        <button type="submit" disabled={adding || !newName.trim()}>
            {adding ? $_('grocery.adding_button') : $_('grocery.add_button')}
        </button>
    </div>
</form>

{#if loading}
    <p class="muted">{$_('common.loading')}</p>
{:else if error}
    <p class="error">{error}</p>
{:else if feed.length === 0}
    <p class="muted">{$_('lists.empty')}</p>
{:else}
    <table>
        <thead>
            <tr>
                <th>{$_('grocery.col_item')}</th>
                {#if listType !== 'wish_list'}
                    <th>{$_('grocery.col_category')}</th>
                    <th>{$_('grocery.col_qty')}</th>
                {:else}
                    <th>{$_('lists.col_url')}</th>
                    <th>{$_('lists.col_priority')}</th>
                {/if}
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
                    {#if listType !== 'wish_list'}
                        <td>
                            {#if entry.category_slug}
                                <span class="cat-chip">{categoryLabel(entry.category_slug)}</span>
                            {/if}
                        </td>
                        <td>{entry.quantity}{entry.unit ? '\u00a0' + entry.unit : ''}</td>
                    {:else}
                        <td>
                            {#if entry.wish_url}
                                <a href={entry.wish_url} target="_blank" rel="noopener noreferrer" class="wish-link">{$_('lists.view_link')}</a>
                            {/if}
                        </td>
                        <td>
                            {#if entry.wish_priority}
                                <span class="priority-chip priority-{entry.wish_priority}">{priorityLabel(entry.wish_priority)}</span>
                            {/if}
                        </td>
                    {/if}
                    <td>
                        {#if entry.collection_id}
                            <a href="/collections/{entry.collection_id}">
                                {collections.get(entry.collection_id)?.name ?? entry.collection_id}
                            </a>
                        {/if}
                    </td>
                    <td class="actions">
                        <button type="button" onclick={() => markPurchased(entry)}>
                            {listType === 'wish_list' ? $_('lists.mark_received_button') : $_('grocery.mark_purchased_button')}
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
        background: none; border: 1px solid var(--border, #d1d5db); border-radius: 6px;
        padding: 0.35rem 0.75rem; font-size: 0.85rem; cursor: pointer; color: var(--text, #111);
    }
    .store-mgr-btn:hover { border-color: var(--accent, #3b82f6); color: var(--accent, #3b82f6); }
    .add-form { margin: 1rem 0 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
    .add-row-main { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .add-row-details { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
    .name-input { flex: 2; min-width: 12rem; }
    .category-select { flex: 1; min-width: 10rem; }
    .custom-cat { flex: 1; min-width: 9rem; }
    .collection-select { min-width: 9rem; }
    .wish-url { flex: 2; min-width: 14rem; }
    .wish-priority { min-width: 9rem; }
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
        background: color-mix(in srgb, var(--accent, #3b82f6) 12%, var(--surface));
        border: 1px solid color-mix(in srgb, var(--accent, #3b82f6) 30%, transparent);
        color: var(--text);
        white-space: nowrap;
    }
    .badge-depleted {
        display: inline-block; font-size: 0.7rem; padding: 0.1rem 0.4rem;
        border-radius: 99px; background: #7c2d12; color: #fed7aa; margin-left: 0.25rem;
    }
    .priority-chip {
        display: inline-block; font-size: 0.75rem; padding: 0.15rem 0.5rem;
        border-radius: 99px; white-space: nowrap;
    }
    .priority-1 { background: #d1fae5; color: #065f46; }
    .priority-2 { background: #fef9c3; color: #854d0e; }
    .priority-3 { background: #fee2e2; color: #991b1b; }
    [data-theme='dark'] .priority-1 { background: #064e3b; color: #6ee7b7; }
    [data-theme='dark'] .priority-2 { background: #451a03; color: #fde68a; }
    [data-theme='dark'] .priority-3 { background: #450a0a; color: #fca5a5; }
    .wish-link { color: var(--accent); font-size: 0.85rem; }
</style>
