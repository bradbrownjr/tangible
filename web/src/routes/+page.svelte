<script lang="ts">
    import { onMount, tick } from 'svelte';
    import { goto } from '$app/navigation';
    import { _ } from 'svelte-i18n';
    import { api, type Item, type Collection } from '$lib/api';

    type SearchField =
        | 'all'
        | 'title'
        | 'brand'
        | 'category'
        | 'notes'
        | 'barcode'
        | 'serial';

    const FIELDS: { value: SearchField; key: string }[] = [
        { value: 'all', key: 'home.search.field.all' },
        { value: 'title', key: 'home.search.field.title' },
        { value: 'brand', key: 'home.search.field.brand' },
        { value: 'category', key: 'home.search.field.category' },
        { value: 'notes', key: 'home.search.field.notes' },
        { value: 'barcode', key: 'home.search.field.barcode' },
        { value: 'serial', key: 'home.search.field.serial' }
    ];

    let q = $state('');
    let field = $state<SearchField>('all');
    let includeArchived = $state(true);
    let results = $state<Item[]>([]);
    let collections = $state<Collection[]>([]);
    let collectionsById = $derived(
        Object.fromEntries(collections.map((c) => [c.id, c])) as Record<string, Collection>
    );
    let loading = $state(false);
    let searched = $state(false);
    let error = $state('');
    let searchInput: HTMLInputElement | undefined;
    let debounceTimer: ReturnType<typeof setTimeout> | undefined;

    // Quick-add dialog (when search returns no results).
    let addOpen = $state(false);
    let addCollectionId = $state('');
    let addAsWish = $state(true);
    let adding = $state(false);

    onMount(async () => {
        try {
            collections = await api.get<Collection[]>('/collections');
            if (collections.length > 0) addCollectionId = collections[0].id;
        } catch {
            // Header layout will surface auth errors; ignore here.
        }
        await tick();
        searchInput?.focus();
    });

    async function runSearch() {
        const term = q.trim();
        if (!term) {
            results = [];
            searched = false;
            error = '';
            return;
        }
        loading = true;
        error = '';
        try {
            const params = new URLSearchParams({
                q: term,
                field,
                limit: '50',
                include_archived: includeArchived ? 'true' : 'false'
            });
            results = await api.get<Item[]>(`/items/search?${params.toString()}`);
            searched = true;
        } catch (e) {
            error = (e as Error).message;
            results = [];
        } finally {
            loading = false;
        }
    }

    function onInput() {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(runSearch, 250);
    }

    function statusOf(item: Item): { label: string; tone: string } {
        if (item.archived_at) return { label: $_('home.status.archived'), tone: 'muted' };
        if (item.wanted) return { label: $_('home.status.wishlist'), tone: 'wish' };
        if (item.depleted) return { label: $_('home.status.depleted'), tone: 'warn' };
        return { label: $_('home.status.owned'), tone: 'ok' };
    }

    function brandOf(item: Item): string | null {
        const a = item.attrs ?? {};
        const b = a['brand'] ?? a['manufacturer'] ?? a['maker'];
        return typeof b === 'string' && b.trim() ? b : null;
    }

    function categoryLabel(item: Item): string | null {
        const slug = item.category_slug;
        if (!slug) return null;
        return slug.split('.').pop() ?? slug;
    }

    function openAddDialog() {
        if (!collections.length) return;
        addOpen = true;
        addAsWish = true;
        if (!addCollectionId) addCollectionId = collections[0].id;
    }

    async function submitAdd(e: Event) {
        e.preventDefault();
        const term = q.trim();
        if (!term || !addCollectionId) return;
        adding = true;
        try {
            const created = await api.post<Item>('/items', {
                collection_id: addCollectionId,
                title: term,
                wanted: addAsWish
            });
            addOpen = false;
            await goto(`/collections/${created.collection_id}#item-${created.id}`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            adding = false;
        }
    }
</script>

<h1>{$_('home.title')}</h1>

<form
    class="search-bar"
    onsubmit={(e) => {
        e.preventDefault();
        runSearch();
    }}
>
    <select bind:value={field} onchange={runSearch} aria-label={$_('home.search.field_label')}>
        {#each FIELDS as f (f.value)}
            <option value={f.value}>{$_(f.key)}</option>
        {/each}
    </select>
    <input
        bind:this={searchInput}
        bind:value={q}
        oninput={onInput}
        type="search"
        placeholder={$_('home.search.placeholder')}
        autocomplete="off"
    />
    <button type="submit">{$_('home.search.submit')}</button>
</form>

<label class="archived-toggle">
    <input type="checkbox" bind:checked={includeArchived} onchange={runSearch} />
    {$_('home.search.include_archived')}
</label>

{#if error}<p class="error">{error}</p>{/if}

{#if loading}
    <p class="muted">{$_('common.loading')}</p>
{:else if searched && q.trim() && results.length === 0}
    <div class="card empty">
        <p><strong>{$_('home.empty.title', { values: { q: q.trim() } })}</strong></p>
        <p class="muted">{$_('home.empty.subtitle')}</p>
        <div class="empty-actions">
            <button type="button" onclick={openAddDialog} disabled={!collections.length}>
                {$_('home.empty.add_button')}
            </button>
        </div>
    </div>
{:else if results.length}
    <ul class="results">
        {#each results as item (item.id)}
            {@const s = statusOf(item)}
            {@const brand = brandOf(item)}
            {@const cat = categoryLabel(item)}
            {@const col = collectionsById[item.collection_id]}
            <li>
                <a class="result" href={`/collections/${item.collection_id}#item-${item.id}`}>
                    <div class="line">
                        <span class="title">{item.title}</span>
                        <span class="status status-{s.tone}">{s.label}</span>
                    </div>
                    <div class="meta muted">
                        {#if brand}<span>{brand}</span>{/if}
                        {#if brand && cat}<span aria-hidden="true"> · </span>{/if}
                        {#if cat}<span>{cat}</span>{/if}
                        {#if (brand || cat) && col}<span aria-hidden="true"> · </span>{/if}
                        {#if col}<span>{col.name}</span>{/if}
                        {#if item.quantity > 1}
                            <span aria-hidden="true"> · </span>
                            <span>×{item.quantity}</span>
                        {/if}
                    </div>
                    {#if item.subtitle || item.notes}
                        <div class="snippet muted">{item.subtitle ?? item.notes}</div>
                    {/if}
                </a>
            </li>
        {/each}
    </ul>
{/if}

<h2>{$_('home.shortcuts.heading')}</h2>
<div class="tiles">
    <a href="/collections" class="tile"><strong>{$_('nav.collections')}</strong></a>
    <a href="/lists/groceries" class="tile"><strong>{$_('lists.type.groceries')}</strong></a>
    <a href="/lists/wish_list" class="tile"><strong>{$_('lists.type.wish_list')}</strong></a>
    <a href="/maintenance" class="tile"><strong>{$_('nav.maintenance')}</strong></a>
    <a href="/import" class="tile"><strong>{$_('nav.import')}</strong></a>
    <a href="/settings/appearance" class="tile"><strong>{$_('nav.settings')}</strong></a>
</div>

{#if addOpen}
    <div class="dialog-backdrop" role="presentation" onclick={() => (addOpen = false)}>
        <form
            class="dialog card"
            role="dialog"
            aria-modal="true"
            onclick={(e) => e.stopPropagation()}
            onsubmit={submitAdd}
        >
            <h3>{$_('home.add_dialog.heading', { values: { q: q.trim() } })}</h3>
            <div class="field">
                <label for="add-collection">{$_('home.add_dialog.collection_label')}</label>
                <select id="add-collection" bind:value={addCollectionId} required>
                    {#each collections as c (c.id)}
                        <option value={c.id}>{c.name}</option>
                    {/each}
                </select>
            </div>
            <label class="check">
                <input type="checkbox" bind:checked={addAsWish} />
                {$_('home.add_dialog.as_wishlist')}
            </label>
            <div class="dialog-actions">
                <button type="button" class="link" onclick={() => (addOpen = false)}>
                    {$_('common.cancel')}
                </button>
                <button type="submit" disabled={adding || !addCollectionId}>
                    {adding ? $_('home.add_dialog.adding') : $_('home.add_dialog.add')}
                </button>
            </div>
        </form>
    </div>
{/if}

<style>
    h1 { margin: 0 0 1rem; }
    h2 { margin: 2rem 0 0.5rem; font-size: 1.1rem; }
    .search-bar {
        display: flex;
        gap: 0.5rem;
        align-items: stretch;
        margin-bottom: 0.5rem;
        flex-wrap: wrap;
    }
    .search-bar input[type='search'] {
        flex: 1 1 240px;
        min-width: 200px;
    }
    .archived-toggle {
        display: inline-flex;
        gap: 0.4rem;
        align-items: center;
        font-size: 0.875rem;
        color: var(--muted);
        margin-bottom: 1rem;
    }
    .results {
        list-style: none;
        padding: 0;
        margin: 1rem 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .result {
        display: block;
        padding: 0.75rem 1rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        color: inherit;
        text-decoration: none;
    }
    .result:hover { border-color: var(--accent); }
    .line {
        display: flex;
        justify-content: space-between;
        gap: 0.5rem;
        align-items: baseline;
    }
    .title { font-weight: 600; }
    .meta { font-size: 0.875rem; margin-top: 0.15rem; }
    .snippet {
        margin-top: 0.25rem;
        font-size: 0.875rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .status {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.1rem 0.45rem;
        border-radius: 999px;
        border: 1px solid var(--border);
        white-space: nowrap;
    }
    .status-ok { color: var(--accent); border-color: var(--accent); }
    .status-warn { color: #b87005; border-color: #b87005; }
    .status-wish { color: #6c4ab6; border-color: #6c4ab6; }
    .status-muted { color: var(--muted); }
    .empty { margin: 1rem 0; }
    .empty-actions { margin-top: 0.75rem; }
    .tiles {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 0.5rem;
    }
    .tile {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1.25rem 0.75rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        text-align: center;
        color: inherit;
        text-decoration: none;
    }
    .tile:hover { border-color: var(--accent); }
    .dialog-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
        padding: 1rem;
    }
    .dialog { max-width: 420px; width: 100%; }
    .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    .check { display: inline-flex; gap: 0.4rem; align-items: center; margin: 0.5rem 0; }
    .link { background: none; border: none; padding: 0; color: var(--accent); cursor: pointer; }
    .field { margin: 0.75rem 0; }
    .field label { display: block; font-size: 0.875rem; margin-bottom: 0.25rem; }
</style>
