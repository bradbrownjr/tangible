<script lang="ts">
    import { onMount, tick } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, type Category, type Collection, type Item, type ItemTemplate } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let templates = $state<ItemTemplate[]>([]);
    let relatedItemTitles = $state<Record<string, string>>({});
    let categories = $state<Category[]>([]);
    let search = $state('');
    let rootFilter = $state(''); // only used when collection has no default category
    let wantedFilter = $state<'all' | 'wanted' | 'owned'>('all');
    let archivedFilter = $state<'active' | 'archived' | 'all'>('active');
    let sortBy = $state<'title' | 'value' | 'acquired_at' | 'attr'>('title');
    let sortDir = $state<'asc' | 'desc'>('asc');
    let sortAttr = $state('');
    let selectedItemIds = $state<string[]>([]);
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
    let editPurchasedAt = $state('');
    let editUseByDate = $state('');
    let editDateFrozen = $state('');
    let editDateOpened = $state('');
    let confirmDialog = $state<'delete-item' | 'delete-collection' | 'flag-item' | 'mark-owned' | 'archive-item' | null>(null);
    let pendingDeleteItemId = $state<string | null>(null);
    let pendingDeleteItemTitle = $state('');
    let pendingFlagItemId = $state<string | null>(null);
    let pendingFlagItemTitle = $state('');
    let flagNoteInput = $state('');
    let pendingOwnedItemId = $state<string | null>(null);
    let pendingOwnedItemTitle = $state('');
    let ownedAtInput = $state('');
    let ownedPriceInput = $state('');
    let pendingArchiveItemId = $state<string | null>(null);
    let pendingArchiveItemTitle = $state('');
    let archiveDispositionType = $state<'sold' | 'disposed' | 'donated' | 'archived'>('archived');
    let archiveDispositionAt = $state('');
    let archiveDispositionAmount = $state('');
    let archiveDispositionBuyer = $state('');
    let archiveDispositionNote = $state('');
    let bulkBusy = $state(false);

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
    let barcodeImageInput: HTMLInputElement | undefined;

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

    // Helper to determine if a category slug is for consumables (pantry, spices, batteries, etc).
    function isConsumable(slug: string | null): boolean {
        if (!slug) return false;
        const root = slug.split('.')[0];
        return root === 'spices'; // spices root includes pantry items
    }

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

    // Check if current leaf is consumable
    const isCurrentLeafConsumable = $derived(isConsumable(newLeaf));

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
    const templateById = $derived.by(() => {
        const byId = new Map<string, ItemTemplate>();
        for (const t of templates) byId.set(t.id, t);
        return byId;
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

    function displayValue(i: Item): number | null {
        return i.rollup_current_value ?? i.current_value;
    }

    function formatValue(i: Item): string {
        const value = displayValue(i);
        if (value == null) return '';
        const currency = i.currency ?? 'USD';
        try {
            return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(value);
        } catch {
            return `${currency} ${value.toFixed(2)}`;
        }
    }

    type RelationEntry = { key: string; label: string; targetId: string };

    function relationEntries(i: Item): RelationEntry[] {
        if (!i.template_id) return [];
        const tmpl = templateById.get(i.template_id);
        if (!tmpl) return [];
        const entries: RelationEntry[] = [];
        for (const f of tmpl.fields) {
            if (f.type !== 'relation') continue;
            const raw = i.attrs?.[f.key];
            if (typeof raw !== 'string') continue;
            const targetId = raw.trim();
            if (!targetId) continue;
            entries.push({ key: f.key, label: f.label || f.key, targetId });
        }
        return entries;
    }

    function relationTitle(targetId: string): string {
        const local = items.find((x) => x.id === targetId);
        if (local) return local.title;
        return relatedItemTitles[targetId] ?? targetId;
    }

    function isSelected(itemId: string): boolean {
        return selectedItemIds.includes(itemId);
    }

    function toggleSelected(itemId: string) {
        if (isSelected(itemId)) {
            selectedItemIds = selectedItemIds.filter((id) => id !== itemId);
        } else {
            selectedItemIds = [...selectedItemIds, itemId];
        }
    }

    function selectVisibleItems() {
        selectedItemIds = items.map((i) => i.id);
    }

    function clearSelection() {
        selectedItemIds = [];
    }

    async function hydrateRelatedItemTitles(currentItems: Item[]) {
        const wanted = new Set<string>();
        for (const i of currentItems) {
            for (const rel of relationEntries(i)) {
                wanted.add(rel.targetId);
            }
        }
        const missing = [...wanted].filter(
            (id) => !currentItems.some((x) => x.id === id) && !relatedItemTitles[id]
        );
        if (missing.length === 0) return;

        const nextTitles = { ...relatedItemTitles };
        await Promise.allSettled(
            missing.map(async (id) => {
                try {
                    const target = await api.get<Item>(`/items/${id}`);
                    nextTitles[id] = target.title;
                } catch {
                    nextTitles[id] = id;
                }
            })
        );
        relatedItemTitles = nextTitles;
    }

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
            if (archivedFilter === 'archived') {
                params.set('include_archived', 'true');
                params.set('archived', 'true');
            } else if (archivedFilter === 'all') {
                params.set('include_archived', 'true');
            }
            if (wantedFilter === 'wanted') params.set('wanted', 'true');
            if (wantedFilter === 'owned') params.set('wanted', 'false');
            params.set('sort_by', sortBy);
            params.set('sort_dir', sortDir);
            if (sortBy === 'attr' && sortAttr.trim()) params.set('sort_attr', sortAttr.trim());
            const [fetchedItems, fetchedTemplates] = await Promise.all([
                api.get<Item[]>(`/items?${params.toString()}`),
                api.get<ItemTemplate[]>(`/collections/${cid}/templates`),
            ]);
            items = fetchedItems;
            templates = fetchedTemplates;
            selectedItemIds = selectedItemIds.filter((id) => fetchedItems.some((i) => i.id === id));
            await hydrateRelatedItemTitles(fetchedItems);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function bulkPatch(payload: { depleted?: boolean; wanted?: boolean }) {
        if (!selectedItemIds.length) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-patch', {
                collection_id: cid,
                item_ids: selectedItemIds,
                ...payload,
            });
            await load();
            clearSelection();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            bulkBusy = false;
        }
    }

    async function bulkDelete() {
        if (!selectedItemIds.length) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-delete', {
                collection_id: cid,
                item_ids: selectedItemIds,
            });
            await load();
            clearSelection();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            bulkBusy = false;
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
            if (kind === 'url') {
                const res = await api.post<{ title?: string; category?: string }>(
                    '/metadata/scrape',
                    { url: newQuery.trim() }
                );
                applyScrapeResult(res);
            } else {
                const digits = newQuery.replace(/[\s-]/g, '');
                const res = await api.post<{ candidates?: Array<{ title?: string; category?: string; attrs?: Record<string, unknown> }> }>(
                    '/metadata/barcode',
                    { barcode: digits }
                );
                const first = res.candidates?.[0];
                if (first) {
                    applyScrapeResult(first);
                } else {
                    throw new Error('No barcode match found');
                }
            }
        } catch (e) {
            error = `Lookup failed: ${(e as Error).message}`;
        } finally {
            scraping = false;
        }
    }

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

    function triggerBarcodeImagePicker() {
        barcodeImageInput?.click();
    }

    async function onBarcodeImagePicked(e: Event) {
        const input = e.currentTarget as HTMLInputElement;
        const file = input.files?.[0];
        input.value = '';
        if (!file) return;
        scraping = true;
        error = '';
        try {
            const code = await decodeBarcodeFromImage(file);
            newQuery = code;
            if (detectKind(code) === 'title') {
                scraping = false;
                return;
            }
            await lookupAndPrefill();
        } catch (err) {
            error = `Image scan failed: ${(err as Error).message}`;
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

    function requestRemoveItem(item: Item) {
        pendingDeleteItemId = item.id;
        pendingDeleteItemTitle = item.title;
        confirmDialog = 'delete-item';
    }

    async function removeItemConfirmed() {
        if (!pendingDeleteItemId) return;
        await api.delete(`/items/${pendingDeleteItemId}`);
        pendingDeleteItemId = null;
        pendingDeleteItemTitle = '';
        confirmDialog = null;
        await load();
    }

    function startEdit(i: Item) {
        editingId = i.id;
        editTitle = i.title;
        editCreator = String(i.attrs?.creator ?? '');
        editSubtitle = i.subtitle ?? '';
        editCondition = i.condition ?? '';
        editQuantity = i.quantity;
        // Convert ISO strings to datetime-local format for input fields (remove Z, handle truncation)
        editPurchasedAt = i.purchased_at ? new Date(i.purchased_at).toISOString().slice(0, 16) : '';
        editUseByDate = i.use_by_date ? new Date(i.use_by_date).toISOString().slice(0, 16) : '';
        editDateFrozen = i.date_frozen ? new Date(i.date_frozen).toISOString().slice(0, 16) : '';
        editDateOpened = i.date_opened ? new Date(i.date_opened).toISOString().slice(0, 16) : '';
    }

    function cancelEdit() {
        editingId = null;
    }

    async function saveEdit() {
        if (!editingId) return;
        const attrsPayload: Record<string, string> = {};
        if (editCreator.trim()) attrsPayload.creator = editCreator.trim();
        const updatePayload: Record<string, unknown> = {
            title: editTitle.trim(),
            subtitle: editSubtitle.trim() || null,
            condition: editCondition.trim() || null,
            quantity: editQuantity,
            attrs: attrsPayload,
        };
        // Add consumable dates if this item is in a consumable category
        const editingItem = items.find((it) => it.id === editingId);
        if (editingItem && isConsumable(editingItem.category_slug)) {
            updatePayload.purchased_at = editPurchasedAt ? new Date(editPurchasedAt).toISOString() : null;
            updatePayload.use_by_date = editUseByDate ? new Date(editUseByDate).toISOString() : null;
            updatePayload.date_frozen = editDateFrozen ? new Date(editDateFrozen).toISOString() : null;
            updatePayload.date_opened = editDateOpened ? new Date(editDateOpened).toISOString() : null;
        }
        await api.patch(`/items/${editingId}`, updatePayload);
        editingId = null;
        await load();
    }

    async function toggleDepleted(item: Item) {
        await api.patch(`/items/${item.id}`, { depleted: !item.depleted });
        await load();
    }

    async function toggleWanted(item: Item) {
        if (item.wanted) {
            pendingOwnedItemId = item.id;
            pendingOwnedItemTitle = item.title;
            ownedAtInput = new Date().toISOString().slice(0, 16);
            ownedPriceInput = '';
            confirmDialog = 'mark-owned';
            return;
        }
        await api.patch(`/items/${item.id}`, { wanted: true });
        await load();
    }

    async function markOwnedConfirmed() {
        if (!pendingOwnedItemId) return;
        const payload: Record<string, unknown> = { wanted: false };
        if (ownedAtInput) payload.acquired_at = new Date(ownedAtInput).toISOString();
        if (ownedPriceInput.trim()) payload.purchase_price = Number(ownedPriceInput);
        await api.patch(`/items/${pendingOwnedItemId}`, payload);
        pendingOwnedItemId = null;
        pendingOwnedItemTitle = '';
        ownedAtInput = '';
        ownedPriceInput = '';
        confirmDialog = null;
        await load();
    }

    function requestFlagItem(item: Item) {
        pendingFlagItemId = item.id;
        pendingFlagItemTitle = item.title;
        flagNoteInput = item.flagged_note ?? '';
        confirmDialog = 'flag-item';
    }

    async function flagItemConfirmed() {
        if (!pendingFlagItemId) return;
        await api.post(`/items/${pendingFlagItemId}/flag`, { note: flagNoteInput });
        pendingFlagItemId = null;
        pendingFlagItemTitle = '';
        flagNoteInput = '';
        confirmDialog = null;
        await load();
    }

    async function clearFlag(item: Item) {
        await api.delete(`/items/${item.id}/flag`);
        await load();
    }

    function requestArchiveItem(item: Item) {
        pendingArchiveItemId = item.id;
        pendingArchiveItemTitle = item.title;
        archiveDispositionType = 'archived';
        archiveDispositionAt = new Date().toISOString().slice(0, 16);
        archiveDispositionAmount = '';
        archiveDispositionBuyer = '';
        archiveDispositionNote = '';
        confirmDialog = 'archive-item';
    }

    async function archiveItemConfirmed() {
        if (!pendingArchiveItemId) return;
        const payload: Record<string, unknown> = {
            disposition_type: archiveDispositionType,
            disposition_at: archiveDispositionAt ? new Date(archiveDispositionAt).toISOString() : undefined,
            disposition_buyer: archiveDispositionBuyer.trim() || undefined,
            disposition_note: archiveDispositionNote.trim() || undefined,
        };
        if (archiveDispositionAmount.trim()) payload.disposition_amount = Number(archiveDispositionAmount);
        await api.post(`/items/${pendingArchiveItemId}/archive`, payload);
        pendingArchiveItemId = null;
        pendingArchiveItemTitle = '';
        confirmDialog = null;
        await load();
    }

    async function restoreArchivedItem(item: Item) {
        await api.post(`/items/${item.id}/restore`, {});
        await load();
    }

    async function duplicateItem(item: Item) {
        const copyTitle = item.title.endsWith(' (Copy)') ? item.title : `${item.title} (Copy)`;
        await api.post('/items', {
            collection_id: item.collection_id,
            category_id: item.category_id,
            title: copyTitle,
            subtitle: item.subtitle,
            notes: item.notes,
            condition: item.condition,
            quantity: item.quantity,
            purchase_price: item.purchase_price,
            current_value: item.current_value,
            currency: item.currency,
            location: item.location,
            identifiers: { ...item.identifiers },
            attrs: { ...item.attrs },
            depleted: item.depleted,
            wanted: item.wanted,
            purchased_at: item.purchased_at,
            use_by_date: item.use_by_date,
            date_frozen: item.date_frozen,
            date_opened: item.date_opened
        });
        await load();
    }

    function requestDeleteCollection() {
        confirmDialog = 'delete-collection';
    }

    async function deleteCollectionConfirmed() {
        if (!collection) return;
        try {
            await api.delete(`/collections/${cid}`);
            confirmDialog = null;
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
            <button type="button" class="tab tab-danger" onclick={requestDeleteCollection}>Delete</button>
        {/if}
    </nav>

    {#if canEdit}
    <form onsubmit={addItem} class="card add-form">
        <input
            bind:this={barcodeImageInput}
            type="file"
            accept="image/*"
            style="display:none"
            onchange={onBarcodeImagePicked}
        />
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
            <button type="button" class="secondary" onclick={triggerBarcodeImagePicker} disabled={scraping}>
                Scan image
            </button>
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
        <select bind:value={sortBy} onchange={() => load()} title="Sort by">
            <option value="title">Sort: Title</option>
            <option value="value">Sort: Current value</option>
            <option value="acquired_at">Sort: Acquisition date</option>
            <option value="attr">Sort: Custom field</option>
        </select>
        <select bind:value={wantedFilter} onchange={() => load()} title="Wanted status">
            <option value="all">All ownership states</option>
            <option value="owned">Owned only</option>
            <option value="wanted">Wanted only</option>
        </select>
        <select bind:value={archivedFilter} onchange={() => load()} title="Archived status">
            <option value="active">Active only</option>
            <option value="archived">Archived only</option>
            <option value="all">Active + archived</option>
        </select>
        <select bind:value={sortDir} onchange={() => load()} title="Sort direction">
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
        </select>
        {#if sortBy === 'attr'}
            <input
                bind:value={sortAttr}
                placeholder="Custom field key (e.g. creator)"
                title="Custom field key"
                onkeydown={(e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        load();
                    }
                }}
                onblur={() => load()}
            />
        {/if}
    </div>

    {#if canEdit}
        <div class="bulk-toolbar">
            <span class="muted">Selected: {selectedItemIds.length}</span>
            <button type="button" class="secondary" onclick={selectVisibleItems} disabled={!items.length || bulkBusy}>Select visible</button>
            <button type="button" class="secondary" onclick={clearSelection} disabled={!selectedItemIds.length || bulkBusy}>Clear</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ depleted: true })} disabled={!selectedItemIds.length || bulkBusy}>Bulk depleted</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ depleted: false })} disabled={!selectedItemIds.length || bulkBusy}>Bulk in stock</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ wanted: true })} disabled={!selectedItemIds.length || bulkBusy}>Bulk wanted</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ wanted: false })} disabled={!selectedItemIds.length || bulkBusy}>Bulk owned</button>
            <button type="button" class="danger" onclick={bulkDelete} disabled={!selectedItemIds.length || bulkBusy}>Bulk delete</button>
        </div>
    {/if}

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
                            {#if isConsumable(i.category_slug)}
                                <input type="datetime-local" bind:value={editPurchasedAt} placeholder="Purchased" class="edit-input" title="Purchased date" />
                                <input type="datetime-local" bind:value={editUseByDate} placeholder="Use by" class="edit-input" title="Use by date" />
                                <input type="datetime-local" bind:value={editDateFrozen} placeholder="Frozen" class="edit-input" title="Date frozen" />
                                <input type="datetime-local" bind:value={editDateOpened} placeholder="Opened" class="edit-input" title="Date opened" />
                            {/if}
                        </div>
                        <div class="item-card-actions">
                            <button onclick={saveEdit}>Save</button>
                            <button type="button" class="secondary" onclick={cancelEdit}>Cancel</button>
                        </div>
                    </div>
                {:else}
                    <div class="item-card" class:depleted-card={i.depleted} class:wanted-card={i.wanted} class:archived-card={i.archived_at != null}>
                        <div class="item-card-body">
                            {#if canEdit}
                                <label class="select-chip">
                                    <input
                                        type="checkbox"
                                        checked={isSelected(i.id)}
                                        onchange={() => toggleSelected(i.id)}
                                    />
                                    Select
                                </label>
                            {/if}
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
                            {#if relationEntries(i).length}
                                <div class="relation-list">
                                    {#each relationEntries(i) as rel (`${rel.key}:${rel.targetId}`)}
                                        <div class="relation-card" title={rel.targetId}>
                                            <span class="relation-label">{rel.label}</span>
                                            <span class="relation-target">{relationTitle(rel.targetId)}</span>
                                        </div>
                                    {/each}
                                </div>
                            {/if}
                            <div class="item-meta">
                                {#if i.condition}<span>{i.condition}</span>{/if}
                                {#if i.quantity > 1}<span>×{i.quantity}</span>{/if}
                                {#if displayValue(i) != null}<span>{formatValue(i)}</span>{/if}
                                {#if i.depleted}<span class="depleted-badge">Depleted</span>{/if}
                                {#if i.wanted}<span class="wanted-badge">Wanted</span>{/if}
                                {#if i.archived_at}<span class="archived-badge">Archived</span>{/if}
                                {#if i.flagged_at}
                                    <span class="flagged-badge" title={i.flagged_note ?? 'Flagged for review'}>
                                        Flagged
                                    </span>
                                {/if}
                                {#if isConsumable(i.category_slug)}
                                    {#if i.use_by_date}<span class="date-badge use-by">Use by {new Date(i.use_by_date).toLocaleDateString()}</span>{/if}
                                    {#if i.date_opened}<span class="date-badge opened">Opened {new Date(i.date_opened).toLocaleDateString()}</span>{/if}
                                {/if}
                            </div>
                        </div>
                        {#if canEdit}
                            <div class="item-card-actions">
                                <button type="button" class="secondary" onclick={() => startEdit(i)}>Edit</button>
                                <button type="button" class="secondary" onclick={() => duplicateItem(i)} disabled={i.archived_at != null}>Duplicate</button>
                                <button
                                    type="button"
                                    class={i.depleted ? 'secondary' : 'warn'}
                                    onclick={() => toggleDepleted(i)}
                                    disabled={i.archived_at != null}
                                >{i.depleted ? 'In stock' : 'Depleted'}</button>
                                <button
                                    type="button"
                                    class={i.wanted ? 'secondary' : 'warn'}
                                    onclick={() => toggleWanted(i)}
                                    disabled={i.archived_at != null}
                                >{i.wanted ? 'Owned' : 'Wanted'}</button>
                                <button
                                    type="button"
                                    class="secondary"
                                    onclick={() => (i.flagged_at ? clearFlag(i) : requestFlagItem(i))}
                                    disabled={i.archived_at != null}
                                >{i.flagged_at ? 'Unflag' : 'Flag'}</button>
                                <button type="button" class="secondary" onclick={() => (i.archived_at ? restoreArchivedItem(i) : requestArchiveItem(i))}>{i.archived_at ? 'Restore' : 'Archive'}</button>
                                <button class="danger item-card-delete" onclick={() => requestRemoveItem(i)}>Delete</button>
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
                    {#if canEdit}<th style="width:1%"><input type="checkbox" checked={items.length > 0 && selectedItemIds.length === items.length} onchange={(e) => ((e.target as HTMLInputElement).checked ? selectVisibleItems() : clearSelection())} /></th>{/if}
                    {#if !isFocused}<th>Category</th>{/if}
                    {#if collectionCreatorLabel}<th>{collectionCreatorLabel}</th>{/if}
                    <th>Title</th>
                    {#if showCollectionSubtitle}<th>Subtitle</th>{/if}
                    <th>Qty</th>
                    <th>Condition</th>
                    <th>Value</th>
                    {#if canEdit}<th></th>{/if}
                </tr>
            </thead>
            <tbody>
                {#each items as i (i.id)}
                    {#if editingId === i.id}
                        <tr class="editing-row">
                            {#if canEdit}<td></td>{/if}
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
                            <td class="muted">{formatValue(i)}</td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button onclick={saveEdit}>Save</button>
                                    <button type="button" class="secondary" onclick={cancelEdit}>Cancel</button>
                                </td>
                            {/if}
                        </tr>
                        {#if isConsumable(i.category_slug)}
                            <tr class="editing-row consumable-dates-row">
                                <td colspan="100" style="padding: 0.5rem;">
                                    <div class="consumable-dates-grid">
                                        <input type="datetime-local" bind:value={editPurchasedAt} placeholder="Purchased" class="edit-input" title="Purchased date" />
                                        <input type="datetime-local" bind:value={editUseByDate} placeholder="Use by" class="edit-input" title="Use by date" />
                                        <input type="datetime-local" bind:value={editDateFrozen} placeholder="Frozen" class="edit-input" title="Date frozen" />
                                        <input type="datetime-local" bind:value={editDateOpened} placeholder="Opened" class="edit-input" title="Date opened" />
                                    </div>
                                </td>
                            </tr>
                        {/if}
                    {:else}
                        <tr class:depleted-row={i.depleted} class:wanted-row={i.wanted} class:archived-row={i.archived_at != null}>
                            {#if canEdit}
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={isSelected(i.id)}
                                        onchange={() => toggleSelected(i.id)}
                                    />
                                </td>
                            {/if}
                            {#if !isFocused}<td class="muted">{i.category_slug ?? ''}</td>{/if}
                            {#if collectionCreatorLabel}<td class="muted">{String(i.attrs?.creator ?? '')}</td>{/if}
                            <td>
                                {i.title}
                                {#if i.subtitle && !showCollectionSubtitle}<span class="muted"> · {i.subtitle}</span>{/if}
                                {#if i.flagged_at}
                                    <span class="flagged-inline" title={i.flagged_note ?? 'Flagged for review'}>Flagged</span>
                                {/if}
                                {#if i.wanted}
                                    <span class="wanted-inline" title="Marked as wanted / not currently owned">Wanted</span>
                                {/if}
                                {#if i.archived_at}
                                    <span class="archived-inline" title={i.disposition_type ?? 'archived'}>Archived</span>
                                {/if}
                                {#if relationEntries(i).length}
                                    <div class="relation-inline-list">
                                        {#each relationEntries(i) as rel (`${rel.key}:${rel.targetId}`)}
                                            <div class="relation-inline-card" title={rel.targetId}>
                                                <span class="relation-label">{rel.label}</span>
                                                <span class="relation-target">{relationTitle(rel.targetId)}</span>
                                            </div>
                                        {/each}
                                    </div>
                                {/if}
                            </td>
                            {#if showCollectionSubtitle}<td class="muted">{i.subtitle ?? ''}</td>{/if}
                            <td>{i.quantity}</td>
                            <td>{i.condition ?? ''}</td>
                            <td class="muted">{formatValue(i)}</td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button class="secondary" onclick={() => startEdit(i)}>Edit</button>
                                    <button class="secondary" onclick={() => duplicateItem(i)} disabled={i.archived_at != null}>Duplicate</button>
                                    <button
                                        type="button"
                                        class={i.depleted ? 'secondary' : 'warn'}
                                        onclick={() => toggleDepleted(i)}
                                        disabled={i.archived_at != null}
                                        title={i.depleted ? 'Mark as in stock' : 'Mark as depleted'}
                                    >{i.depleted ? 'In stock' : 'Depleted'}</button>
                                    <button
                                        type="button"
                                        class={i.wanted ? 'secondary' : 'warn'}
                                        onclick={() => toggleWanted(i)}
                                        disabled={i.archived_at != null}
                                        title={i.wanted ? 'Mark as owned' : 'Mark as wanted'}
                                    >{i.wanted ? 'Owned' : 'Wanted'}</button>
                                    <button
                                        type="button"
                                        class="secondary"
                                        onclick={() => (i.flagged_at ? clearFlag(i) : requestFlagItem(i))}
                                        disabled={i.archived_at != null}
                                    >{i.flagged_at ? 'Unflag' : 'Flag'}</button>
                                    <button type="button" class="secondary" onclick={() => (i.archived_at ? restoreArchivedItem(i) : requestArchiveItem(i))}>{i.archived_at ? 'Restore' : 'Archive'}</button>
                                    <button class="danger" onclick={() => requestRemoveItem(i)}>Delete</button>
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

{#if confirmDialog === 'delete-item'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-item-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-item-title">Delete item?</h3>
            <p class="muted">{pendingDeleteItemTitle || 'This item'} will be permanently removed.</p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>Cancel</button>
                <button type="button" class="danger" onclick={removeItemConfirmed}>Delete</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'delete-collection'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-collection-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-collection-title">Delete collection?</h3>
            <p class="muted">
                This permanently removes all items, photos, shares, and related data in {collection?.name}.
            </p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>Cancel</button>
                <button type="button" class="danger" onclick={deleteCollectionConfirmed}>Delete collection</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'flag-item'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="flag-item-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="flag-item-title">Flag item for review</h3>
            <p class="muted">{pendingFlagItemTitle || 'This item'} will be marked for follow-up.</p>
            <label>
                Note (optional)
                <input bind:value={flagNoteInput} maxlength="256" placeholder="e.g. verify location" />
            </label>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>Cancel</button>
                <button type="button" onclick={flagItemConfirmed}>Flag item</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'mark-owned'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="mark-owned-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="mark-owned-title">Mark item as owned</h3>
            <p class="muted">Update ownership details for {pendingOwnedItemTitle || 'this item'}.</p>
            <label>
                Acquisition date
                <input type="datetime-local" bind:value={ownedAtInput} />
            </label>
            <label>
                Purchase price (optional)
                <input type="number" min="0" step="0.01" bind:value={ownedPriceInput} placeholder="e.g. 29.99" />
            </label>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>Cancel</button>
                <button type="button" onclick={markOwnedConfirmed}>Mark owned</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'archive-item'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="archive-item-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="archive-item-title">Archive item</h3>
            <p class="muted">Archive {pendingArchiveItemTitle || 'this item'} and optionally capture disposition details.</p>
            <label>
                Disposition type
                <select bind:value={archiveDispositionType}>
                    <option value="archived">Archived</option>
                    <option value="sold">Sold</option>
                    <option value="disposed">Disposed</option>
                    <option value="donated">Donated</option>
                </select>
            </label>
            <label>
                Disposition date
                <input type="datetime-local" bind:value={archiveDispositionAt} />
            </label>
            <label>
                Amount (optional)
                <input type="number" min="0" step="0.01" bind:value={archiveDispositionAmount} placeholder="e.g. 25.00" />
            </label>
            <label>
                Buyer / recipient (optional)
                <input bind:value={archiveDispositionBuyer} maxlength="256" placeholder="e.g. Alice" />
            </label>
            <label>
                Note (optional)
                <input bind:value={archiveDispositionNote} maxlength="512" placeholder="e.g. donated to local library" />
            </label>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>Cancel</button>
                <button type="button" onclick={archiveItemConfirmed}>Archive</button>
            </div>
        </div>
    </div>
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
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: grid;
        place-items: center;
        padding: 1rem;
        z-index: 40;
    }
    .modal {
        width: min(34rem, 100%);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        display: grid;
        gap: 0.75rem;
    }
    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
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
    .bulk-toolbar {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    .select-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
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
    .relation-list {
        display: grid;
        gap: 0.3rem;
        margin-top: 0.2rem;
    }
    .relation-card,
    .relation-inline-card {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.45rem;
        align-items: baseline;
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--accent) 6%, var(--surface));
        border-radius: 6px;
        padding: 0.2rem 0.4rem;
    }
    .relation-inline-list {
        display: grid;
        gap: 0.2rem;
        margin-top: 0.3rem;
        max-width: 32rem;
    }
    .relation-label {
        font-size: 0.72rem;
        color: var(--text-muted, #888);
        white-space: nowrap;
    }
    .relation-target {
        font-size: 0.8rem;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
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
    .wanted-row td {
        background: color-mix(in srgb, #2c7a7b 8%, transparent);
    }
    .archived-row td {
        opacity: 0.75;
        background: color-mix(in srgb, #666 8%, transparent);
    }
    .flagged-badge {
        display: inline-flex;
        align-items: center;
        background: color-mix(in srgb, var(--warn, #c67a00) 18%, transparent);
        color: var(--warn, #c67a00);
        border: 1px solid color-mix(in srgb, var(--warn, #c67a00) 45%, transparent);
        border-radius: 999px;
        padding: 0.05rem 0.45rem;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .flagged-inline {
        margin-left: 0.4rem;
        font-size: 0.72rem;
        font-weight: 600;
        color: var(--warn, #c67a00);
    }
    .depleted-card {
        opacity: 0.6;
    }
    .wanted-card {
        border-color: color-mix(in srgb, #2c7a7b 35%, var(--border));
    }
    .archived-card {
        border-style: dashed;
    }
    .depleted-card .item-title {
        text-decoration: line-through;
        text-decoration-color: var(--danger, #c00);
    }
    .depleted-badge {
        color: var(--danger, #c00);
        font-weight: 600;
    }
    .wanted-badge,
    .wanted-inline {
        color: #2c7a7b;
        font-weight: 600;
    }
    .archived-badge,
    .archived-inline {
        color: #666;
        font-weight: 600;
    }
    .wanted-inline {
        margin-left: 0.4rem;
        font-size: 0.72rem;
    }
    .archived-inline {
        margin-left: 0.4rem;
        font-size: 0.72rem;
    }
    .date-badge {
        font-size: 0.7rem;
        font-weight: 500;
        padding: 0.2em 0.4em;
        border-radius: 3px;
        background: color-mix(in srgb, currentColor 12%, transparent);
    }
    .date-badge.use-by {
        color: color-mix(in srgb, orange 70%, var(--fg));
    }
    .date-badge.opened {
        color: color-mix(in srgb, #0066cc 70%, var(--fg));
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
    /* Consumable date fields */
    .consumable-dates-row {
        background: color-mix(in srgb, var(--accent) 3%, var(--surface));
    }
    .consumable-dates-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.5rem;
    }
    .consumable-dates-grid .edit-input {
        font-size: 0.875rem;
    }
</style>
