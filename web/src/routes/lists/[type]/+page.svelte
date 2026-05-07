<script lang="ts">
    import { onMount, untrack } from 'svelte';
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { api, type Collection } from '$lib/api';
    import { categoriesForType } from '$lib/shoppingCategories';
    import { _ } from 'svelte-i18n';
    import Icon from '$lib/Icon.svelte';
    import IconButton from '$lib/components/IconButton.svelte';
    import DataTable from '$lib/components/DataTable.svelte';
    import type { Column } from '$lib/components/data-table-types.js';
    import FiltersPanel from '$lib/components/FiltersPanel.svelte';
    import Modal from '$lib/components/Modal.svelte';
    import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
    import Button from '$lib/components/Button.svelte';
    import EmptyState from '$lib/components/EmptyState.svelte';
    import FormField from '$lib/components/FormField.svelte';

    const VALID_TYPES = ['groceries', 'hardware', 'home_goods', 'wish_list'] as const;
    type ListType = typeof VALID_TYPES[number];

    const BACKING_COLLECTION: Record<string, string> = {
        groceries: 'Pantry',
        hardware: 'Hardware',
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
        brand: string | null;
        notes: string | null;
        category_slug: string | null;
        list_type: string;
        wish_url: string | null;
        wish_priority: number | null;
        linked_item_id: string | null;
        purchased_at: string | null;
        created_at: string;
        [key: string]: unknown;
    }

    let listType = $derived((page.params.type ?? 'groceries') as ListType);
    let loadGen = 0;

    // Filter + sort state (client-side, no API round-trip needed for small lists)
    let listSearch = $state('');
    let listSortBy = $state<'name' | 'quantity' | 'created_at' | 'category_slug'>('name');
    let listSortDir = $state<'asc' | 'desc'>('asc');
    let listCategoryFilter = $state('');

    let listActiveCount = $derived(
        (listSearch.trim() ? 1 : 0) +
        (listSortBy !== 'name' || listSortDir !== 'asc' ? 1 : 0) +
        (listCategoryFilter ? 1 : 0)
    );

    const LIST_ICON: Record<string, string> = {
        groceries: 'shopping-cart',
        hardware: 'wrench',
        home_goods: 'house',
        wish_list: 'star',
    };

    let categories = $derived(categoriesForType(listType));

    function typeTitle(t: string): string {
        switch (t) {
            case 'groceries': return $_('lists.type.groceries');
            case 'hardware':  return $_('lists.type.hardware');
            case 'home_goods': return $_('lists.type.home_goods');
            case 'wish_list': return $_('lists.type.wish_list');
            default:          return t;
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

    /** Returns a contextual label for the brand field based on category hints. */
    function brandLabel(slug: string | null): string {
        if (!slug) return '';
        if (/music|album|vinyl|cd|record|jazz|rock|hip.?hop|classical/i.test(slug)) return 'Artist';
        if (/book|novel|comic|manga|author/i.test(slug)) return 'Author';
        if (/movie|film|dvd|blu.?ray|cinema/i.test(slug)) return 'Studio';
        return '';
    }

    let feed = $state<FeedEntry[]>([]);
    let collections = $state<Map<string, Collection>>(new Map());
    let loading = $state(true);

    let filteredFeed = $derived.by(() => {
        let result = feed;
        const q = listSearch.trim().toLowerCase();
        if (q) {
            result = result.filter(
                (e) =>
                    e.name.toLowerCase().includes(q) ||
                    (e.brand ?? '').toLowerCase().includes(q) ||
                    (e.notes ?? '').toLowerCase().includes(q)
            );
        }
        if (listCategoryFilter) {
            result = result.filter((e) => e.category_slug === listCategoryFilter);
        }
        result = [...result].sort((a, b) => {
            let av: string | number = '';
            let bv: string | number = '';
            if (listSortBy === 'name') { av = a.name.toLowerCase(); bv = b.name.toLowerCase(); }
            else if (listSortBy === 'quantity') { av = a.quantity; bv = b.quantity; }
            else if (listSortBy === 'created_at') { av = a.created_at; bv = b.created_at; }
            else if (listSortBy === 'category_slug') { av = a.category_slug ?? ''; bv = b.category_slug ?? ''; }
            if (av < bv) return listSortDir === 'asc' ? -1 : 1;
            if (av > bv) return listSortDir === 'asc' ? 1 : -1;
            return 0;
        });
        return result;
    });
    let error = $state('');

    let newCollectionId = $state('');
    let newName = $state('');
    let newBrand = $state('');
    let newCategorySlug = $state('');
    let customCategory = $state('');
    let newQuantity = $state(1);
    let newUnit = $state('');
    let newNotes = $state('');
    let newWishUrl = $state('');
    let newWishPriority = $state<number | ''>('');
    let adding = $state(false);
    let scanningBarcode = $state(false);
    let barcodeImageInput: HTMLInputElement | undefined;

    async function decodeBarcodeFromImage(file: File): Promise<string> {
        const { BrowserMultiFormatReader } = await import('@zxing/browser');
        const reader = new BrowserMultiFormatReader();
        const dataUrl = await new Promise<string>((resolve, reject) => {
            const fr = new FileReader();
            fr.onload = () => resolve(String(fr.result));
            fr.onerror = () => reject(new Error('Could not read image file'));
            fr.readAsDataURL(file);
        });
        const img = await new Promise<HTMLImageElement>((resolve, reject) => {
            const el = new Image();
            el.onload = () => resolve(el);
            el.onerror = () => reject(new Error('Could not decode image'));
            el.src = dataUrl;
        });
        const result = await reader.decodeFromImageElement(img);
        return result.getText();
    }

    async function onBarcodeImagePicked(e: Event) {
        const input = e.currentTarget as HTMLInputElement;
        const file = input.files?.[0];
        input.value = '';
        if (!file) return;
        scanningBarcode = true;
        error = '';
        try {
            const code = await decodeBarcodeFromImage(file);
            const digits = code.replace(/[\s-]/g, '');
            const res = await api.post<{ candidates?: Array<{ title?: string; category?: string; attrs?: Record<string, unknown> }> }>(
                '/metadata/barcode',
                { barcode: digits }
            );
            const first = res.candidates?.[0];
            if (first) {
                if (first.title) newName = first.title;
                if (first.attrs?.brand) newBrand = String(first.attrs.brand);
                if (first.category) newCategorySlug = first.category;
            } else {
                newName = code; // fall back: put the raw code in the name field
            }
        } catch (err) {
            error = (err as Error).message;
        } finally {
            scanningBarcode = false;
        }
    }

    // Edit state
    let editOpen = $state(false);
    let editEntry = $state<FeedEntry | null>(null);
    let editName = $state('');
    let editBrand = $state('');
    let editCategorySlug = $state('');
    let editCustomCategory = $state('');
    let editQuantity = $state(1);
    let editUnit = $state('');
    let editNotes = $state('');
    let editWishUrl = $state('');
    let editWishPriority = $state<number | ''>('');
    let saving = $state(false);

    // Delete confirm state
    let confirmDeleteEntry = $state<FeedEntry | null>(null);
    let confirmDeleteOpen = $state(false);

    function startEdit(entry: FeedEntry) {
        editEntry = entry;
        editName = entry.name;
        editBrand = entry.brand ?? '';
        editQuantity = entry.quantity;
        editUnit = entry.unit ?? '';
        editNotes = entry.notes ?? '';
        editWishUrl = entry.wish_url ?? '';
        editWishPriority = entry.wish_priority ?? '';
        const preset = categories.find((c) => c.slug === entry.category_slug);
        if (entry.category_slug && !preset) {
            editCategorySlug = 'custom';
            editCustomCategory = entry.category_slug;
        } else {
            editCategorySlug = entry.category_slug ?? '';
            editCustomCategory = '';
        }
        editOpen = true;
    }

    function cancelEdit() {
        editOpen = false;
        editEntry = null;
    }

    async function saveEdit(e: SubmitEvent) {
        e.preventDefault();
        if (!editEntry || !editName.trim()) return;
        const resolvedSlug =
            editCategorySlug === 'custom'
                ? (editCustomCategory.trim().toLowerCase().replace(/\s+/g, '-') || null)
                : (editCategorySlug || null);
        saving = true;
        try {
            const body: Record<string, unknown> = {
                name: editName.trim(),
                quantity: Math.max(1, editQuantity || 1),
                unit: editUnit.trim() || null,
                brand: editBrand.trim() || null,
                notes: editNotes.trim() || null,
                category_slug: resolvedSlug,
            };
            if (editEntry.list_type === 'wish_list') {
                body.wish_url = editWishUrl.trim() || null;
                body.wish_priority = editWishPriority || null;
            }
            await api.patch(`/lists/${editEntry.id}`, body);
            cancelEdit();
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            saving = false;
        }
    }

    async function load() {
        const snapType = listType;
        const snapGen = loadGen;
        loading = true;
        try {
            const [fetched, fetchedCollections] = await Promise.all([
                api.get<FeedEntry[]>(`/lists?list_type=${snapType}`),
                api.get<Collection[]>('/collections'),
            ]);
            if (snapGen !== loadGen) return;
            feed = fetched;
            collections = new Map(fetchedCollections.map((c) => [c.id, c]));
            const backingName = BACKING_COLLECTION[snapType];
            const backing = backingName
                ? fetchedCollections.find((c) => c.name.toLowerCase() === backingName.toLowerCase())
                : null;
            if (!newCollectionId) {
                newCollectionId = backing?.id ?? (fetchedCollections[0]?.id ?? '');
            }
        } catch (e) {
            if (snapGen === loadGen) error = (e as Error).message;
        } finally {
            if (snapGen === loadGen) loading = false;
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
                brand: newBrand.trim() || null,
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
            newBrand = '';
            newQuantity = 1;
            newUnit = '';
            newNotes = '';
            newWishUrl = '';
            newWishPriority = '';
            newCategorySlug = '';
            customCategory = '';
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

    function openDelete(entry: FeedEntry) {
        confirmDeleteEntry = entry;
        confirmDeleteOpen = true;
    }

    $effect(() => {
        const _type = listType;
        loadGen += 1;
        feed = [];
        newCollectionId = '';
        newCategorySlug = '';
        // Reset filters when switching list types
        listSearch = '';
        listCategoryFilter = '';
        listSortBy = 'name';
        listSortDir = 'asc';
        untrack(() => load());
    });

    onMount(() => {
        if (!VALID_TYPES.includes(listType as ListType)) {
            goto('/lists/groceries');
        }
    });
</script>

<svelte:head>
    <title>Tangible · {typeTitle(listType)}</title>
</svelte:head>

<p class="muted">{$_(`lists.description.${listType}`)}</p>

<form class="add-form" onsubmit={addItem}>
    <input
        bind:this={barcodeImageInput}
        type="file"
        accept="image/*"
        style="display:none"
        onchange={onBarcodeImagePicked}
    />
    <div class="add-row-main">
        <input
            class="name-input"
            type="text"
            bind:value={newName}
            placeholder={$_('lists.item_name_placeholder')}
            required
        />
        {#if listType !== 'wish_list'}
            <select class="category-select" bind:value={newCategorySlug}>
                <option value="">{$_('grocery.no_category')}</option>
                {#each categories as cat (cat.slug)}
                    <option value={cat.slug}>{cat.label}</option>
                {/each}
                <option value="custom">{$_('grocery.custom_option')}</option>
            </select>
        {/if}
        <Button variant="secondary" type="button" disabled={scanningBarcode} onclick={() => barcodeImageInput?.click()}>
            {$_('collection.scan_image_button')}
        </Button>
        <Button type="submit" loading={adding} disabled={adding || scanningBarcode || !newName.trim()}>
            {$_('grocery.add_button')}
        </Button>
    </div>

    <details class="more-options">
        <summary>{$_('common.more_options')}</summary>
        <div class="add-details-grid">
            <input type="text" bind:value={newBrand} placeholder={$_('grocery.brand_placeholder')} />
            <input type="text" bind:value={newNotes} placeholder={$_('grocery.notes_placeholder')} />
            {#if newCategorySlug === 'custom'}
                <input type="text" bind:value={customCategory} placeholder={$_('grocery.custom_placeholder')} />
            {/if}
            {#if listType !== 'wish_list'}
                <div class="qty-row">
                    <input type="number" min="1" bind:value={newQuantity} class="qty" aria-label={$_('grocery.col_qty')} />
                    <input type="text" bind:value={newUnit} placeholder={$_('grocery.unit_placeholder')} class="unit" />
                </div>
                {#if collections.size > 1}
                    <select bind:value={newCollectionId} aria-label={$_('grocery.col_collection')}>
                        {#each [...collections.values()] as c (c.id)}
                            <option value={c.id}>{c.name}</option>
                        {/each}
                    </select>
                {/if}
            {/if}
            {#if listType === 'wish_list'}
                <input type="url" bind:value={newWishUrl} placeholder={$_('lists.wish_url_placeholder')} />
                <select bind:value={newWishPriority}>
                    <option value="">{$_('lists.wish_priority_any')}</option>
                    <option value={1}>{$_('lists.priority.low')}</option>
                    <option value={2}>{$_('lists.priority.medium')}</option>
                    <option value={3}>{$_('lists.priority.high')}</option>
                </select>
            {/if}
        </div>
    </details>
</form>

{#if error}
    <p class="error">{error}</p>
{/if}

{#if loading}
    <p class="muted">{$_('common.loading')}</p>
{:else}
    <FiltersPanel activeCount={listActiveCount}>
        {#snippet children()}
            <input
                type="search"
                bind:value={listSearch}
                placeholder={$_('filters.search_placeholder')}
                class="list-search-input"
            />
            {#if listType !== 'wish_list'}
                <select bind:value={listCategoryFilter} class="list-filter-select">
                    <option value="">{$_('filters.all_categories')}</option>
                    {#each categories as cat (cat.slug)}
                        <option value={cat.slug}>{cat.label}</option>
                    {/each}
                </select>
            {/if}
            <select bind:value={listSortBy} class="list-filter-select">
                <option value="name">{$_('filters.sort_name')}</option>
                <option value="quantity">{$_('filters.sort_qty')}</option>
                <option value="created_at">{$_('filters.sort_added')}</option>
                {#if listType !== 'wish_list'}<option value="category_slug">{$_('filters.sort_category')}</option>{/if}
            </select>
            <select bind:value={listSortDir} class="list-filter-select">
                <option value="asc">{$_('filters.sort_asc')}</option>
                <option value="desc">{$_('filters.sort_desc')}</option>
            </select>
        {/snippet}
    </FiltersPanel>

    {#if filteredFeed.length === 0}
        <EmptyState icon={LIST_ICON[listType] ?? 'inbox'} heading={$_('lists.empty')} />
    {:else}
    {#snippet brandCell(entry: FeedEntry)}
        {#if entry.brand}
            {@const lbl = brandLabel(entry.category_slug)}
            <span class="cell-brand">{entry.brand}{#if lbl}&nbsp;<span class="brand-label">{lbl}</span>{/if}</span>
        {/if}
    {/snippet}

    {#snippet nameCell(entry: FeedEntry)}
        <strong class="cell-name">{entry.name}</strong>
        {#if entry.subtitle}<span class="muted"> · {entry.subtitle}</span>{/if}
        {#if entry.source.kind === 'depleted_item'}
            <span class="badge-depleted">{$_('grocery.source_depleted')}</span>
        {/if}
    {/snippet}

    {#snippet categoryCell(entry: FeedEntry)}
        {#if entry.category_slug}
            <span class="cat-chip">{categoryLabel(entry.category_slug)}</span>
        {/if}
    {/snippet}

    {#snippet qtyCell(entry: FeedEntry)}
        {entry.quantity}{entry.unit ? '\u00a0' + entry.unit : ''}
    {/snippet}

    {#snippet urlCell(entry: FeedEntry)}
        {#if entry.wish_url}
            <a href={entry.wish_url} target="_blank" rel="noopener noreferrer" class="wish-link">
                {$_('lists.view_link')}
            </a>
        {/if}
    {/snippet}

    {#snippet priorityCell(entry: FeedEntry)}
        {#if entry.wish_priority}
            <span class="priority-chip priority-{entry.wish_priority}">{priorityLabel(entry.wish_priority)}</span>
        {/if}
    {/snippet}

    {#snippet notesCell(entry: FeedEntry)}
        {#if entry.notes}
            <span class="cell-notes">{entry.notes}</span>
        {/if}
    {/snippet}

    {#snippet collectionCell(entry: FeedEntry)}
        {#if entry.collection_id}
            <a href="/collections/{entry.collection_id}">
                {collections.get(entry.collection_id)?.name ?? entry.collection_id}
            </a>
        {/if}
    {/snippet}

    {#snippet rowActions(entry: FeedEntry)}
        <div class="row-actions">
            <IconButton
                name={listType === 'wish_list' ? 'package-check' : 'check-circle'}
                label={listType === 'wish_list' ? $_('lists.mark_received_button') : $_('grocery.mark_purchased_button')}
                variant="primary"
                btnSize="sm"
                onclick={() => markPurchased(entry)}
            />
            {#if entry.source.kind === 'ad_hoc'}
                <IconButton name="pencil" label={$_('grocery.edit_button')} variant="secondary" btnSize="sm" onclick={() => startEdit(entry)} />
                <IconButton name="trash-2" label={$_('grocery.remove_button')} variant="danger" btnSize="sm" onclick={() => openDelete(entry)} />
            {/if}
        </div>
    {/snippet}

    <DataTable
        cols={listType !== 'wish_list'
            ? ([
                { key: 'brand',         label: $_('grocery.col_brand'),      cell: brandCell,    tdClass: 'col-brand', mobileLabel: $_('grocery.col_brand') },
                { key: 'name',          label: $_('grocery.col_item'),        cell: nameCell,     tdClass: 'col-name' },
                { key: 'category_slug', label: $_('grocery.col_category'),    cell: categoryCell, tdClass: 'col-cat' },
                { key: 'quantity',      label: $_('grocery.col_qty'),         cell: qtyCell,      tdClass: 'col-qty', align: 'right' },
                { key: 'notes',         label: $_('grocery.col_notes'),       cell: notesCell,    tdClass: 'col-notes' },
              ] satisfies Column<FeedEntry>[])
            : ([
                { key: 'name',          label: $_('grocery.col_item'),        cell: nameCell,     tdClass: 'col-name' },
                { key: 'wish_url',      label: $_('lists.col_url'),           cell: urlCell },
                { key: 'wish_priority', label: $_('lists.col_priority'),      cell: priorityCell },
              ] satisfies Column<FeedEntry>[])}
        rows={filteredFeed}
        rowKey="id"
        actions={rowActions}
    />
    {/if}
{/if}

<Modal bind:open={editOpen} title={$_('grocery.edit_item_title')} onclose={cancelEdit}>
    <form id="edit-list-item-form" onsubmit={saveEdit} class="edit-form-body">
        <FormField label={$_('grocery.brand_placeholder')}>
            <input type="text" bind:value={editBrand} />
        </FormField>
        <FormField label={$_('lists.item_name_placeholder')} required>
            <input type="text" bind:value={editName} required />
        </FormField>
        {#if listType !== 'wish_list'}
            <FormField label={$_('grocery.col_category')}>
                <select bind:value={editCategorySlug}>
                    <option value="">{$_('grocery.no_category')}</option>
                    {#each categories as cat (cat.slug)}
                        <option value={cat.slug}>{cat.label}</option>
                    {/each}
                    <option value="custom">{$_('grocery.custom_option')}</option>
                </select>
            </FormField>
            {#if editCategorySlug === 'custom'}
                <FormField label={$_('grocery.custom_placeholder')}>
                    <input type="text" bind:value={editCustomCategory} />
                </FormField>
            {/if}
        {/if}
        <FormField label={$_('grocery.notes_placeholder')}>
            <input type="text" bind:value={editNotes} />
        </FormField>
        {#if listType !== 'wish_list'}
            <div class="edit-row">
                <FormField label={$_('grocery.col_qty')}>
                    <input type="number" min="1" bind:value={editQuantity} />
                </FormField>
                <FormField label={$_('grocery.unit_placeholder')}>
                    <input type="text" bind:value={editUnit} />
                </FormField>
            </div>
        {/if}
        {#if listType === 'wish_list'}
            <FormField label={$_('lists.wish_url_placeholder')}>
                <input type="url" bind:value={editWishUrl} />
            </FormField>
            <FormField label={$_('lists.col_priority')}>
                <select bind:value={editWishPriority}>
                    <option value="">{$_('lists.wish_priority_any')}</option>
                    <option value={1}>{$_('lists.priority.low')}</option>
                    <option value={2}>{$_('lists.priority.medium')}</option>
                    <option value={3}>{$_('lists.priority.high')}</option>
                </select>
            </FormField>
        {/if}
    </form>
    {#snippet footer()}
        <Button type="submit" form="edit-list-item-form" loading={saving} disabled={saving || !editName.trim()}>
            {$_('common.save')}
        </Button>
        <Button variant="secondary" onclick={cancelEdit}>{$_('common.cancel')}</Button>
    {/snippet}
</Modal>

<ConfirmDialog
    open={confirmDeleteOpen}
    title="{$_('grocery.remove_button')} — {confirmDeleteEntry?.name ?? ''}"
    message={$_('grocery.remove_confirm')}
    confirmLabel={$_('grocery.remove_button')}
    variant="danger"
    onconfirm={async () => {
        if (confirmDeleteEntry) await removeItem(confirmDeleteEntry);
        confirmDeleteOpen = false;
        confirmDeleteEntry = null;
    }}
    oncancel={() => { confirmDeleteOpen = false; confirmDeleteEntry = null; }}
/>

<style>
    /* --- column sizing and truncation for the DataTable --- */
    :global(.col-brand) { width: 9ch; max-width: 11ch; }
    :global(.col-name)  { min-width: 0; max-width: 28ch; }
    :global(.col-cat)   { width: 10ch; }
    :global(.col-qty)   { width: 5ch; }
    :global(.col-notes) { min-width: 0; max-width: 20ch; }

    /* --- filter controls inside FiltersPanel --- */
    .list-search-input {
        flex: 1;
        min-width: 140px;
    }
    .list-filter-select {
        width: auto;
        min-width: 7rem;
        flex-shrink: 0;
    }

    .cell-brand {
        display: block;
        font-size: var(--text-xs);
        color: var(--text-muted);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .brand-label {
        font-size: 0.65rem;
        opacity: 0.75;
    }
    .cell-name {
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 100%;
    }
    .cell-notes {
        display: block;
        font-size: var(--text-xs);
        color: var(--text-muted);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* --- add form --- */
    .add-form {
        margin: 1rem 0 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .add-row-main {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        align-items: center;
    }
    .name-input {
        flex: 2;
        min-width: 12rem;
    }
    .category-select {
        flex: 1;
        min-width: 10rem;
    }
    .more-options {
        border: 1px solid var(--border);
        border-radius: var(--radius-md, 8px);
        background: var(--surface);
    }
    .more-options summary {
        padding: 0.5rem 0.75rem;
        cursor: pointer;
        font-size: 0.875rem;
        color: var(--text-muted);
        list-style: none;
        user-select: none;
    }
    .more-options summary::-webkit-details-marker { display: none; }
    .more-options summary::before { content: '+ '; }
    .more-options[open] summary::before { content: '- '; }
    .add-details-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        padding: 0.75rem;
        border-top: 1px solid var(--border);
    }
    .add-details-grid input,
    .add-details-grid select {
        flex: 1;
        min-width: 9rem;
    }
    .qty-row { display: flex; gap: 0.4rem; }
    .qty { width: 4.5rem !important; flex: none !important; }
    .unit { width: 6rem !important; flex: none !important; }
    .row-actions { display: flex; gap: 0.25rem; flex-wrap: nowrap; }
    .cat-chip {
        display: inline-block;
        font-size: 0.75rem;
        padding: 0.15rem 0.5rem;
        border-radius: 99px;
        background: color-mix(in srgb, var(--accent) 12%, var(--surface));
        border: 1px solid color-mix(in srgb, var(--accent) 30%, transparent);
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
    .wish-link { color: var(--accent); font-size: 0.875rem; }
    .small { font-size: 0.85rem; }
    .edit-form-body { display: flex; flex-direction: column; gap: 0.75rem; }
    .edit-row { display: flex; gap: 0.75rem; }
    .edit-row > :global(.form-field) { flex: 1; }
</style>
