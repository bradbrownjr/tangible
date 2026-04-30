<script lang="ts">
    import { onMount, tick } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, type Category, type Collection, type Item } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let categories = $state<Category[]>([]);
    let search = $state('');
    let rootFilter = $state(''); // only used when collection has no default category
    let loading = $state(true);
    let error = $state('');
    let didSeedDefaults = $state(false);
    let viewMode = $state<'list' | 'grid'>('list');

    // Inline item editing
    let editingId = $state<string | null>(null);
    let editTitle = $state('');
    let editCreator = $state('');
    let editSubtitle = $state('');
    let editCondition = $state('');
    let editQuantity = $state(1);

    // Inline create form: cascading root → leaf.
    let newRoot = $state('other');
    let newLeaf = $state('other.generic');
    let newQuery = $state(''); // smart input: URL / ISBN / EAN / Title
    let newCreator = $state('');
    let newSubtitle = $state('');
    let scraping = $state(false);

    let creatorInput: HTMLInputElement | undefined;
    let titleInput: HTMLInputElement | undefined;
    let subtitleInput: HTMLInputElement | undefined;

    // Label for the creator field based on leaf category; null = hide the field.
    const creatorLabel = $derived.by(() => {
        if (newLeaf.startsWith('music.')) return 'Artist / Band';
        if (newLeaf.startsWith('books.')) return 'Author';
        if (newLeaf.startsWith('movies.')) return 'Director';
        if (newLeaf.startsWith('games.')) return 'Developer';
        if (newLeaf.startsWith('tabletop.')) return 'Designer';
        return null;
    });
    // Label for the subtitle/series field; null = hide.
    const subtitleLabel = $derived.by(() => {
        if (newLeaf.startsWith('books.') || newLeaf.startsWith('movies.') || newLeaf.startsWith('games.'))
            return 'Series / subtitle (optional)';
        return null;
    });

    const cid = $derived(page.params.id ?? '');
    const roots = $derived(rootCategories(categories));
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );
    const leaves = $derived.by(() => {
        const root = categories.find((c) => c.slug === newRoot);
        if (!root) return [];
        return childrenOf(categories, root.id);
    });
    // True when this collection is "focused" on a single root (preset wizard).
    const isFocused = $derived.by(() => {
        const def = collection?.default_category_slug;
        if (!def) return false;
        const c = categories.find((x) => x.slug === def);
        return !!c;
    });

    // Column headers for the items table based on the collection's root category.
    const collectionCreatorLabel = $derived.by(() => {
        const root = (collection?.default_category_slug ?? '').split('.')[0];
        if (root === 'music') return 'Artist / Band';
        if (root === 'books') return 'Author';
        if (root === 'movies') return 'Director';
        if (root === 'games') return 'Developer';
        if (root === 'tabletop') return 'Designer';
        return null;
    });
    const showCollectionSubtitle = $derived.by(() => {
        const root = (collection?.default_category_slug ?? '').split('.')[0];
        return root === 'books' || root === 'movies' || root === 'games';
    });

    $effect(() => {
        if (leaves.length && !leaves.some((l) => l.slug === newLeaf)) {
            newLeaf = leaves[0].slug;
        }
    });

    function detectKind(q: string): 'url' | 'isbn' | 'ean' | 'title' {
        const s = q.trim();
        if (/^https?:\/\//i.test(s)) return 'url';
        const digits = s.replace(/[\s-]/g, '');
        if (/^(?:97[89])\d{10}$/.test(digits)) return 'isbn'; // ISBN-13
        if (/^\d{9}[\dXx]$/.test(digits)) return 'isbn'; // ISBN-10
        if (/^\d{12,13}$/.test(digits)) return 'ean';
        return 'title';
    }
    const detected = $derived(detectKind(newQuery));

    async function load() {
        loading = true;
        try {
            if (categories.length === 0) categories = await loadCategories();
            collection = await api.get<Collection>(`/collections/${cid}`);
            const def = collection?.default_category_slug;
            if (def && !didSeedDefaults) {
                const cat = categories.find((c) => c.slug === def);
                if (cat) {
                    if (cat.parent_id === null) {
                        newRoot = cat.slug;
                    } else {
                        const parent = categories.find((c) => c.id === cat.parent_id);
                        if (parent) newRoot = parent.slug;
                        newLeaf = cat.slug;
                    }
                }
                didSeedDefaults = true;
            }
            const params = new URLSearchParams({ collection_id: cid });
            if (search) params.set('search', search);
            if (rootFilter) params.set('category_subtree', rootFilter);
            items = await api.get<Item[]>(`/items?${params.toString()}`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    function applyScrapeResult(res: { title?: string; category?: string; attrs?: Record<string, unknown> }) {
        if (res.title) newQuery = res.title;
        if (res.attrs?.authors) newCreator = String(res.attrs.authors);
        if (res.category) {
            const leaf = categories.find((c) => c.slug === res.category);
            if (leaf?.parent_id) {
                const root = categories.find((c) => c.id === leaf.parent_id);
                if (root) newRoot = root.slug;
                newLeaf = leaf.slug;
            }
        }
    }

    async function lookupAndPrefill() {
        const kind = detected;
        if (kind === 'title') return;
        scraping = true;
        error = '';
        try {
            let url = '';
            if (kind === 'url') {
                url = newQuery.trim();
            } else {
                const digits = newQuery.replace(/[\s-]/g, '');
                url = `https://openlibrary.org/isbn/${digits}`;
            }
            const res = await api.post<{ title?: string; category?: string }>(
                '/metadata/scrape',
                { url }
            );
            applyScrapeResult(res);
        } catch (e) {
            error = `Lookup failed: ${(e as Error).message}`;
        } finally {
            scraping = false;
        }
    }

    async function performAdd() {
        const q = newQuery.trim();
        if (!q) return;
        if (detected !== 'title') {
            await lookupAndPrefill();
        }
        const title = newQuery.trim();
        if (!title || /^https?:\/\//i.test(title)) {
            error = 'Could not derive a title — please enter one manually.';
            return;
        }
        const identifiers: Record<string, string> = {};
        const original = q.replace(/[\s-]/g, '');
        const orig_kind = detectKind(q);
        if (orig_kind === 'isbn') identifiers.isbn = original;
        else if (orig_kind === 'ean') identifiers.ean = original;
        const attrs: Record<string, string> = {};
        if (newCreator.trim()) attrs.creator = newCreator.trim();
        await api.post('/items', {
            collection_id: cid,
            category: newLeaf,
            title,
            subtitle: newSubtitle.trim() || undefined,
            attrs: Object.keys(attrs).length ? attrs : undefined,
            identifiers
        });
        newQuery = '';
        newCreator = '';
        newSubtitle = '';
        await load();
        await tick();
        (creatorLabel ? creatorInput : titleInput)?.focus();
    }

    async function addItem(e: Event) {
        e.preventDefault();
        await performAdd();
    }

    async function removeItem(id: string) {
        if (!confirm('Delete this item?')) return;
        await api.delete(`/items/${id}`);
        await load();
    }

    function startEdit(i: Item) {
        editingId = i.id;
        editTitle = i.title;
        editCreator = String(i.attrs?.creator ?? '');
        editSubtitle = i.subtitle ?? '';
        editCondition = i.condition ?? '';
        editQuantity = i.quantity;
    }

    function cancelEdit() {
        editingId = null;
    }

    async function saveEdit() {
        if (!editingId) return;
        const attrsPayload: Record<string, string> = {};
        if (editCreator.trim()) attrsPayload.creator = editCreator.trim();
        await api.patch(`/items/${editingId}`, {
            title: editTitle.trim(),
            subtitle: editSubtitle.trim() || null,
            condition: editCondition.trim() || null,
            quantity: editQuantity,
            attrs: attrsPayload,
        });
        editingId = null;
        await load();
    }

    async function toggleDepleted(item: Item) {
        await api.patch(`/items/${item.id}`, { depleted: !item.depleted });
        await load();
    }

    async function deleteCollection() {
        if (!collection) return;
        const name = collection.name;
        if (
            !confirm(
                `Delete the "${name}" collection? This permanently removes all items, photos, and shares it owns.`
            )
        )
            return;
        try {
            await api.delete(`/collections/${cid}`);
            await goto('/');
        } catch (e) {
            error = (e as Error).message;
        }
    }

    onMount(() => {
        viewMode = (localStorage.getItem('covet:viewMode') ?? 'list') as 'list' | 'grid';
        load();
    });

    $effect(() => {
        localStorage.setItem('covet:viewMode', viewMode);
    });
</script>

{#if collection}
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}

    <nav class="subnav" aria-label="Collection sections">
        <a class="tab tab-active" href="/collections/{cid}" aria-current="page">Items</a>
        <a class="tab" href="/collections/{cid}/templates">Templates</a>
        <a class="tab" href="/collections/{cid}/members">Members</a>
        {#if collection.my_role === 'owner'}
            <button type="button" class="tab tab-danger" onclick={deleteCollection}>Delete</button>
        {/if}
    </nav>

    {#if canEdit}
    <form onsubmit={addItem} class="card add-form">
        <label class="add-label" for="addq">
            Add an item
            <span class="muted">— paste a URL, scan a barcode, type an ISBN/EAN, or just a title</span>
        </label>
        <div class="add-row">
            {#if !isFocused}
                <select bind:value={newRoot} title="Category root">
                    {#each roots as r (r.id)}
                        <option value={r.slug}>{r.name}</option>
                    {/each}
                </select>
            {/if}
            <select bind:value={newLeaf} title="Category">
                {#each leaves as l (l.id)}
                    <option value={l.slug}>{l.name}</option>
                {/each}
            </select>
            {#if creatorLabel}
                <input
                    bind:this={creatorInput}
                    bind:value={newCreator}
                    placeholder={creatorLabel}
                    autocomplete="off"
                    class="creator-field"
                    onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); titleInput?.focus(); } }}
                />
            {/if}
            <input
                id="addq"
                bind:this={titleInput}
                bind:value={newQuery}
                placeholder="URL · ISBN · EAN · or title…"
                autocomplete="off"
                class="title-field"
                onkeydown={(e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        if (subtitleLabel && subtitleInput) subtitleInput.focus();
                        else performAdd();
                    }
                }}
            />
            {#if subtitleLabel}
                <input
                    bind:this={subtitleInput}
                    bind:value={newSubtitle}
                    placeholder={subtitleLabel}
                    autocomplete="off"
                    class="subtitle-field"
                    onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); performAdd(); } }}
                />
            {/if}
            {#if detected !== 'title' && newQuery.trim()}
                <button type="button" onclick={lookupAndPrefill} disabled={scraping}>
                    {scraping ? 'Looking up…' : `Look up ${detected.toUpperCase()}`}
                </button>
            {/if}
            <button type="submit" disabled={scraping || !newQuery.trim()}>Add</button>
        </div>
        {#if error}<p class="error">{error}</p>{/if}
    </form>
    {/if}

    <div class="filters">
        <input
            bind:value={search}
            placeholder="Search this collection (title)…"
            oninput={() => load()}
        />
        {#if !isFocused}
            <select bind:value={rootFilter} onchange={() => load()}>
                <option value="">All categories</option>
                {#each roots as r (r.id)}
                    <option value={r.slug}>{r.name}</option>
                {/each}
            </select>
        {/if}
        <div class="view-toggle" role="group" aria-label="View mode">
            <button type="button" class="toggle-btn" class:active={viewMode === 'list'} onclick={() => viewMode = 'list'} title="List view" aria-label="List view">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <rect x="0" y="2" width="16" height="2" rx="1"/>
                    <rect x="0" y="7" width="16" height="2" rx="1"/>
                    <rect x="0" y="12" width="16" height="2" rx="1"/>
                </svg>
            </button>
            <button type="button" class="toggle-btn" class:active={viewMode === 'grid'} onclick={() => viewMode = 'grid'} title="Grid view" aria-label="Grid view">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <rect x="0" y="0" width="7" height="7" rx="1"/>
                    <rect x="9" y="0" width="7" height="7" rx="1"/>
                    <rect x="0" y="9" width="7" height="7" rx="1"/>
                    <rect x="9" y="9" width="7" height="7" rx="1"/>
                </svg>
            </button>
        </div>
    </div>

    {#if loading}
        <p class="muted">Loading…</p>
    {:else if items.length === 0}
        <p class="muted">No items yet.</p>
    {:else if viewMode === 'grid'}
        <div class="item-grid">
            {#each items as i (i.id)}
                {#if editingId === i.id}
                    <div class="item-card item-card-edit">
                        <div class="item-card-body">
                            {#if collectionCreatorLabel}
                                <input bind:value={editCreator} placeholder={collectionCreatorLabel} class="edit-input" />
                            {/if}
                            <input bind:value={editTitle} placeholder="Title" class="edit-input" />
                            {#if showCollectionSubtitle}
                                <input bind:value={editSubtitle} placeholder="Series / subtitle" class="edit-input" />
                            {/if}
                            <input bind:value={editCondition} placeholder="Condition" class="edit-input" />
                            <input type="number" bind:value={editQuantity} min="0" placeholder="Qty" class="edit-input" style="width:5rem" />
                        </div>
                        <div class="item-card-actions">
                            <button onclick={saveEdit}>Save</button>
                            <button type="button" class="secondary" onclick={cancelEdit}>Cancel</button>
                        </div>
                    </div>
                {:else}
                    <div class="item-card" class:depleted-card={i.depleted}>
                        <div class="item-card-body">
                            {#if !isFocused && i.category_slug}
                                <span class="category-badge">{i.category_slug.split('.').at(-1) ?? i.category_slug}</span>
                            {/if}
                            {#if i.attrs?.creator}
                                <p class="item-creator">{String(i.attrs.creator)}</p>
                            {/if}
                            <p class="item-title">{i.title}</p>
                            {#if i.subtitle}
                                <p class="item-subtitle">{i.subtitle}</p>
                            {/if}
                            <div class="item-meta">
                                {#if i.condition}<span>{i.condition}</span>{/if}
                                {#if i.quantity > 1}<span>×{i.quantity}</span>{/if}
                                {#if i.depleted}<span class="depleted-badge">Depleted</span>{/if}
                            </div>
                        </div>
                        {#if canEdit}
                            <div class="item-card-actions">
                                <button type="button" class="secondary" onclick={() => startEdit(i)}>Edit</button>
                                <button
                                    type="button"
                                    class={i.depleted ? 'secondary' : 'warn'}
                                    onclick={() => toggleDepleted(i)}
                                >{i.depleted ? 'In stock' : 'Depleted'}</button>
                                <button class="danger item-card-delete" onclick={() => removeItem(i.id)}>Delete</button>
                            </div>
                        {/if}
                    </div>
                {/if}
            {/each}
        </div>
    {:else}
        <table>
            <thead>
                <tr>
                    {#if !isFocused}<th>Category</th>{/if}
                    {#if collectionCreatorLabel}<th>{collectionCreatorLabel}</th>{/if}
                    <th>Title</th>
                    {#if showCollectionSubtitle}<th>Subtitle</th>{/if}
                    <th>Qty</th>
                    <th>Condition</th>
                    {#if canEdit}<th></th>{/if}
                </tr>
            </thead>
            <tbody>
                {#each items as i (i.id)}
                    {#if editingId === i.id}
                        <tr class="editing-row">
                            {#if !isFocused}<td></td>{/if}
                            {#if collectionCreatorLabel}
                                <td><input bind:value={editCreator} placeholder={collectionCreatorLabel} class="edit-input" /></td>
                            {/if}
                            <td><input bind:value={editTitle} placeholder="Title" class="edit-input" /></td>
                            {#if showCollectionSubtitle}
                                <td><input bind:value={editSubtitle} placeholder="Series / subtitle" class="edit-input" /></td>
                            {/if}
                            <td><input type="number" bind:value={editQuantity} min="0" placeholder="Qty" class="edit-input qty-input" /></td>
                            <td><input bind:value={editCondition} placeholder="Condition" class="edit-input" /></td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button onclick={saveEdit}>Save</button>
                                    <button type="button" class="secondary" onclick={cancelEdit}>Cancel</button>
                                </td>
                            {/if}
                        </tr>
                    {:else}
                        <tr class:depleted-row={i.depleted}>
                            {#if !isFocused}<td class="muted">{i.category_slug ?? ''}</td>{/if}
                            {#if collectionCreatorLabel}<td class="muted">{String(i.attrs?.creator ?? '')}</td>{/if}
                            <td>{i.title}{#if i.subtitle && !showCollectionSubtitle}<span class="muted"> · {i.subtitle}</span>{/if}</td>
                            {#if showCollectionSubtitle}<td class="muted">{i.subtitle ?? ''}</td>{/if}
                            <td>{i.quantity}</td>
                            <td>{i.condition ?? ''}</td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button class="secondary" onclick={() => startEdit(i)}>Edit</button>
                                    <button
                                        type="button"
                                        class={i.depleted ? 'secondary' : 'warn'}
                                        onclick={() => toggleDepleted(i)}
                                        title={i.depleted ? 'Mark as in stock' : 'Mark as depleted'}
                                    >{i.depleted ? 'In stock' : 'Depleted'}</button>
                                    <button class="danger" onclick={() => removeItem(i.id)}>Delete</button>
                                </td>
                            {/if}
                        </tr>
                    {/if}
                {/each}
            </tbody>
        </table>
    {/if}
{:else if !loading}
    <p class="error">Collection not found.</p>
{/if}

<style>
    .subnav {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
        margin: 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }
    .tab {
        display: inline-flex;
        align-items: center;
        padding: 0.4rem 0.8rem;
        font: inherit;
        font-weight: 500;
        color: var(--fg);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        text-decoration: none;
        cursor: pointer;
    }
    .tab:hover {
        border-color: var(--accent);
    }
    .tab-active {
        background: var(--accent);
        color: var(--accent-fg, white);
        border-color: var(--accent);
    }
    .tab-danger {
        color: var(--danger);
        border-color: var(--danger);
        margin-left: auto;
    }
    .tab-danger:hover {
        background: var(--danger);
        color: white;
    }
    .edit-input {
        width: 100%;
        box-sizing: border-box;
        padding: 0.3rem 0.5rem;
        font: inherit;
        font-size: 0.875rem;
    }
    .qty-input {
        width: 4rem;
    }
    .editing-row td {
        background: color-mix(in srgb, var(--accent) 6%, var(--surface));
    }
    .row-actions {
        white-space: nowrap;
        display: flex;
        gap: 0.35rem;
    }
    .item-card-actions {
        display: flex;
        gap: 0;
        border-top: 1px solid var(--border);
    }
    .item-card-actions button {
        flex: 1;
        border-radius: 0;
        font-size: 0.8rem;
        padding: 0.4rem;
        border: none;
        border-right: 1px solid var(--border);
    }
    .item-card-actions button:last-child {
        border-right: none;
    }
    .add-form {
        margin: 1rem 0;
    }
    .add-label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: 500;
    }
    .add-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .add-row select {
        flex: 0 0 auto;
        min-width: 130px;
        max-width: 180px;
    }
    .creator-field {
        flex: 1 1 150px;
        min-width: 120px;
        max-width: 210px;
    }
    .title-field {
        flex: 2 1 180px;
        min-width: 140px;
    }
    .subtitle-field {
        flex: 2 1 180px;
        min-width: 140px;
    }
    .creator-tag {
        font-weight: 500;
    }
    .filters {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
        align-items: center;
    }
    .filters > input {
        flex: 1;
    }
    .view-toggle {
        display: flex;
        gap: 0;
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
        flex-shrink: 0;
    }
    .toggle-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.4rem 0.6rem;
        background: var(--surface);
        border: none;
        border-radius: 0;
        color: var(--text-muted, #888);
        cursor: pointer;
    }
    .toggle-btn:hover {
        color: var(--accent);
    }
    .toggle-btn.active {
        background: var(--accent);
        color: var(--accent-fg, white);
    }
    /* Grid / card view */
    .item-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 0.75rem;
    }
    .item-card {
        display: flex;
        flex-direction: column;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
    }
    .item-card-body {
        flex: 1;
        padding: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    .category-badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--accent);
        background: color-mix(in srgb, var(--accent) 12%, transparent);
        border-radius: 4px;
        padding: 0.15em 0.45em;
        align-self: flex-start;
    }
    .item-creator {
        font-size: 0.8rem;
        color: var(--text-muted, #888);
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .item-title {
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0;
        line-height: 1.3;
    }
    .item-subtitle {
        font-size: 0.8rem;
        color: var(--text-muted, #888);
        margin: 0;
    }
    .item-meta {
        display: flex;
        gap: 0.5rem;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
        margin-top: auto;
        padding-top: 0.25rem;
    }
    .item-card-delete {
        width: 100%;
        border-radius: 0;
        border-top: 1px solid var(--border);
        font-size: 0.8rem;
        padding: 0.4rem;
    }
    /* Depleted items */
    .depleted-row td {
        opacity: 0.55;
        text-decoration: line-through;
        text-decoration-color: var(--danger, #c00);
    }
    .depleted-card {
        opacity: 0.6;
    }
    .depleted-card .item-title {
        text-decoration: line-through;
        text-decoration-color: var(--danger, #c00);
    }
    .depleted-badge {
        color: var(--danger, #c00);
        font-weight: 600;
    }
    button.warn {
        background: color-mix(in srgb, orange 15%, var(--surface));
        border-color: orange;
        color: color-mix(in srgb, orange 60%, var(--fg));
    }
    button.warn:hover {
        background: orange;
        color: white;
    }
</style>
