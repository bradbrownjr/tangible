<script lang="ts">
    import { onMount, tick } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Category, type Collection, type Contact, type Item, type ItemTemplate, type LocationNode, type Tag } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';
    import ItemComments from '$lib/ItemComments.svelte';
    import PhotoGallery from '$lib/PhotoGallery.svelte';
    import { me } from '$lib/session';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let templates = $state<ItemTemplate[]>([]);
    let tags = $state<Tag[]>([]);
    let contacts = $state<Contact[]>([]);
    let relatedItemTitles = $state<Record<string, string>>({});
    let categories = $state<Category[]>([]);
    let search = $state('');
    let rootFilter = $state(''); // only used when collection has no default category
    let wantedFilter = $state<'all' | 'wanted' | 'owned'>('all');
    let archivedFilter = $state<'active' | 'archived' | 'all'>('active');
    let sortBy = $state<'sort_order' | 'title' | 'value' | 'acquired_at' | 'attr'>('title');
    let sortDir = $state<'asc' | 'desc'>('asc');
    let sortAttr = $state('');
    let activeTagIds = $state<string[]>([]);
    let tagMode = $state<'all' | 'any'>('all');
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
    let selectedBulkTagId = $state('');
    let bulkMoveLocationId = $state('');
    let locations = $state<LocationNode[]>([]);
    let selectedBulkContactId = $state('');
    let bulkLoanDueAt = $state('');

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
    let searchInput: HTMLInputElement | undefined;

    // Label for the creator field based on leaf category; null = hide the field.
    const creatorLabel = $derived.by(() => {
        if (newLeaf.startsWith('music.')) return $_('collection.creator_artist');
        if (newLeaf.startsWith('books.')) return $_('collection.creator_author');
        if (newLeaf.startsWith('movies.')) return $_('collection.creator_director');
        if (newLeaf.startsWith('games.')) return $_('collection.creator_developer');
        if (newLeaf.startsWith('tabletop.')) return $_('collection.creator_designer');
        return null;
    });
    // Label for the subtitle/series field; null = hide.
    const subtitleLabel = $derived.by(() => {
        if (newLeaf.startsWith('books.') || newLeaf.startsWith('movies.') || newLeaf.startsWith('games.'))
            return $_('collection.subtitle_placeholder');
        return null;
    });

    // Helper to determine if a category slug is for consumables (pantry, spices, batteries, etc).
    function isConsumable(slug: string | null): boolean {
        if (!slug) return false;
        const root = slug.split('.')[0];
        return root === 'spices'; // spices root includes pantry items
    }

    // Quick-action config for maintenance-relevant categories.
    const QUICK_ACTIONS: Record<string, { label: () => string; choreName: (title: string) => string; intervalDays: number }> = {
        'home_equipment.hvac': {
            label: () => $_('collection.quick_action_filter_change'),
            choreName: (title) => `${title} — filter change`,
            intervalDays: 60,
        },
        'home_equipment.refrigerator': {
            label: () => $_('collection.quick_action_filter_change'),
            choreName: (title) => `${title} — filter change`,
            intervalDays: 180,
        },
        'home_equipment.water_filtration': {
            label: () => $_('collection.quick_action_filter_service'),
            choreName: (title) => `${title} — filter service`,
            intervalDays: 90,
        },
        'home_equipment.generator': {
            label: () => $_('collection.quick_action_run_generator'),
            choreName: (title) => `${title} — run log`,
            intervalDays: 30,
        },
    };

    function quickActionFor(slug: string | null) {
        if (!slug) return null;
        return QUICK_ACTIONS[slug] ?? null;
    }

    async function triggerQuickAction(item: Item) {
        const action = quickActionFor(item.category_slug);
        if (!action) return;
        try {
            await api.post(`/items/${item.id}/quick-chore`, {
                chore_name: action.choreName(item.title),
                interval_days: action.intervalDays,
            });
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    const cid = $derived(page.params.id ?? '');
    const roots = $derived(rootCategories(categories));
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );
    const locationOptions = $derived.by(() => {
        const out: { id: string; label: string }[] = [];
        const walk = (nodes: LocationNode[], depth: number) => {
            for (const n of nodes) {
                out.push({ id: n.id, label: `${'\u00a0\u00a0'.repeat(depth)}${n.name}` });
                walk(n.children, depth + 1);
            }
        };
        walk(locations, 0);
        return out;
    });
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
        if (root === 'music') return $_('collection.creator_artist');
        if (root === 'books') return $_('collection.creator_author');
        if (root === 'movies') return $_('collection.creator_director');
        if (root === 'games') return $_('collection.creator_developer');
        if (root === 'tabletop') return $_('collection.creator_designer');
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
            if (activeTagIds.length) {
                for (const tid of activeTagIds) params.append('tag_ids', tid);
                params.set('tag_mode', tagMode);
            }
            const [fetchedItems, fetchedTemplates, fetchedTags, fetchedContacts, fetchedLocations] = await Promise.all([
                api.get<Item[]>(`/items?${params.toString()}`),
                api.get<ItemTemplate[]>(`/collections/${cid}/templates`),
                api.get<Tag[]>('/tags'),
                api.get<Contact[]>('/contacts'),
                api.get<LocationNode[]>(`/locations?collection_id=${cid}`),
            ]);
            items = fetchedItems;
            templates = fetchedTemplates;
            tags = fetchedTags;
            contacts = fetchedContacts;
            locations = fetchedLocations;
            if (selectedBulkTagId && !fetchedTags.some((t) => t.id === selectedBulkTagId)) {
                selectedBulkTagId = '';
            }
            if (selectedBulkContactId && !fetchedContacts.some((c) => c.id === selectedBulkContactId)) {
                selectedBulkContactId = '';
            }
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

    async function bulkArchive() {
        if (!selectedItemIds.length) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-archive', {
                collection_id: cid,
                item_ids: selectedItemIds,
                disposition_type: 'archived',
            });
            await load();
            clearSelection();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            bulkBusy = false;
        }
    }

    async function bulkRestore() {
        if (!selectedItemIds.length) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-restore', {
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

    async function bulkTag(mode: 'add' | 'remove') {
        if (!selectedItemIds.length || !selectedBulkTagId) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-tags', {
                collection_id: cid,
                item_ids: selectedItemIds,
                tag_ids: [selectedBulkTagId],
                mode,
            });
            await load();
            clearSelection();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            bulkBusy = false;
        }
    }

    async function runBulkMoveLocation(clear = false) {
        if (!selectedItemIds.length) return;
        if (!clear && !bulkMoveLocationId) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-patch', {
                collection_id: cid,
                item_ids: selectedItemIds,
                location_id: clear ? null : bulkMoveLocationId,
            });
            await load();
            clearSelection();
            if (clear) bulkMoveLocationId = '';
        } catch (e) {
            error = (e as Error).message;
        } finally {
            bulkBusy = false;
        }
    }

    async function bulkLend() {
        if (!selectedItemIds.length || !selectedBulkContactId) return;
        bulkBusy = true;
        error = '';
        try {
            await api.post('/items/bulk-lend', {
                collection_id: cid,
                item_ids: selectedItemIds,
                contact_id: selectedBulkContactId,
                due_at: bulkLoanDueAt ? new Date(bulkLoanDueAt).toISOString() : undefined,
            });
            await load();
            clearSelection();
            bulkLoanDueAt = '';
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
            error = $_('collection.scraping_error', { values: { error: (e as Error).message } });
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
            error = $_('collection.image_scan_error', { values: { error: (err as Error).message } });
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
            error = $_('collection.title_derivation_error');
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

    let conditionSuggestions = $state<string[]>([]);
    let creatorSuggestions = $state<string[]>([]);

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
        // Lazy-load suggestions on first edit (silent — non-critical, user just gets no autocomplete).
        if (!conditionSuggestions.length) {
            api.get<string[]>(`/collections/${cid}/field-suggestions?field=condition`, true)
                .then((v) => { conditionSuggestions = v; })
                .catch(() => {});
        }
        if (collectionCreatorLabel && !creatorSuggestions.length) {
            api.get<string[]>(`/collections/${cid}/field-suggestions?field=creator`, true)
                .then((v) => { creatorSuggestions = v; })
                .catch(() => {});
        }
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
            location_id: item.location_id,
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
        viewMode = (localStorage.getItem('tangible:viewMode') ?? 'list') as 'list' | 'grid';
        const onGlobalKeydown = (event: KeyboardEvent) => {
            if (event.key !== '/') return;
            if (event.metaKey || event.ctrlKey || event.altKey) return;
            const active = document.activeElement;
            if (active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement) return;
            event.preventDefault();
            searchInput?.focus();
            searchInput?.select();
        };
        window.addEventListener('keydown', onGlobalKeydown);
        load();
        return () => window.removeEventListener('keydown', onGlobalKeydown);
    });

    function filterBySearch(value: string) {
        search = value;
        void load();
    }

    function filterByCategory(slug: string) {
        rootFilter = slug;
        void load();
    }

    function toggleTagFilter(tagId: string) {
        if (activeTagIds.includes(tagId)) {
            activeTagIds = activeTagIds.filter((t) => t !== tagId);
        } else {
            activeTagIds = [...activeTagIds, tagId];
        }
        void load();
    }

    $effect(() => {
        localStorage.setItem('tangible:viewMode', viewMode);
    });
</script>

{#if collection}
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}

    <nav class="subnav" aria-label="Collection sections">
        <a class="tab tab-active" href="/collections/{cid}" aria-current="page">{$_('collection.tab_items')}</a>
        <a class="tab" href="/collections/{cid}/templates">{$_('collection.tab_templates')}</a>
        <a class="tab" href="/collections/{cid}/locations">{$_('collection.tab_locations')}</a>
        <a class="tab" href="/collections/{cid}/bundles">{$_('collection.tab_bundles')}</a>
        <a class="tab" href="/collections/{cid}/chores">{$_('collection.tab_chores')}</a>
        <a class="tab" href="/collections/{cid}/members">{$_('collection.tab_members')}</a>
        <a class="tab" href="/import?collection={cid}">{$_('collection.tab_import')}</a>
        <a class="tab" href="/api/collections/{cid}/reports/insurance-export" download title="Download insurance-ready ZIP (CSV + photos)">{$_('collection.tab_export')}</a>
        {#if collection.my_role === 'owner'}
            <button type="button" class="tab tab-danger" onclick={requestDeleteCollection}>{$_('collection.delete_collection')}</button>
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
            {$_('collection.add_item_label')}
            <span class="muted">— {$_('collection.add_item_help')}</span>
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
                placeholder={$_('collection.item_title_placeholder')}
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
                    {scraping ? $_('collection.looking_up_button') : $_('collection.lookup_button', { values: { type: detected.toUpperCase() } })}
                </button>
            {/if}
            <button type="button" class="secondary" onclick={triggerBarcodeImagePicker} disabled={scraping}>
                {$_('collection.scan_image_button')}
            </button>
            <button type="submit" disabled={scraping || !newQuery.trim()}>{$_('collection.add_button')}</button>
        </div>
        {#if error}<p class="error">{error}</p>{/if}
    </form>
    {/if}

    <div class="filters">
        <input
            bind:this={searchInput}
            bind:value={search}
            placeholder={$_('collection.search_placeholder')}
            oninput={() => load()}
        />
        {#if !isFocused}
            <select bind:value={rootFilter} onchange={() => load()}>
                <option value="">{$_('collection.all_categories')}</option>
                {#each roots as r (r.id)}
                    <option value={r.slug}>{r.name}</option>
                {/each}
            </select>
        {/if}
        <div class="view-toggle" role="group" aria-label="View mode">
            <button type="button" class="toggle-btn" class:active={viewMode === 'list'} onclick={() => viewMode = 'list'} title={$_('collection.view_list')} aria-label={$_('collection.view_list')}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <rect x="0" y="2" width="16" height="2" rx="1"/>
                    <rect x="0" y="7" width="16" height="2" rx="1"/>
                    <rect x="0" y="12" width="16" height="2" rx="1"/>
                </svg>
            </button>
            <button type="button" class="toggle-btn" class:active={viewMode === 'grid'} onclick={() => viewMode = 'grid'} title={$_('collection.view_grid')} aria-label={$_('collection.view_grid')}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <rect x="0" y="0" width="7" height="7" rx="1"/>
                    <rect x="9" y="0" width="7" height="7" rx="1"/>
                    <rect x="0" y="9" width="7" height="7" rx="1"/>
                    <rect x="9" y="9" width="7" height="7" rx="1"/>
                </svg>
            </button>
        </div>
        <select bind:value={sortBy} onchange={() => load()} title="Sort by">
            <option value="title">{$_('collection.sort_title')}</option>
            <option value="sort_order">{$_('collection.sort_custom')}</option>
            <option value="value">{$_('collection.sort_value')}</option>
            <option value="acquired_at">{$_('collection.sort_acquired')}</option>
            <option value="attr">{$_('collection.sort_attr')}</option>
        </select>
        <select bind:value={wantedFilter} onchange={() => load()} title="Wanted status">
            <option value="all">{$_('collection.filter_all_ownership')}</option>
            <option value="owned">{$_('collection.filter_owned')}</option>
            <option value="wanted">{$_('collection.filter_wanted')}</option>
        </select>
        <select bind:value={archivedFilter} onchange={() => load()} title="Archived status">
            <option value="active">{$_('collection.filter_active')}</option>
            <option value="archived">{$_('collection.filter_archived')}</option>
            <option value="all">{$_('collection.filter_active_archived')}</option>
        </select>
        <select bind:value={sortDir} onchange={() => load()} title="Sort direction">
            <option value="asc">{$_('collection.sort_asc')}</option>
            <option value="desc">{$_('collection.sort_desc')}</option>
        </select>
        {#if sortBy === 'attr'}
            <input
                bind:value={sortAttr}
                placeholder={$_('collection.sort_attr_key_placeholder')}
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
    {#if tags.length}
        <div class="tag-filters">
            {#each tags as t (t.id)}
                <button
                    type="button"
                    class="tag-chip"
                    class:active={activeTagIds.includes(t.id)}
                    onclick={() => toggleTagFilter(t.id)}
                >{t.name}</button>
            {/each}
            {#if activeTagIds.length > 1}
                <button
                    type="button"
                    class="tag-mode-toggle"
                    onclick={() => { tagMode = tagMode === 'all' ? 'any' : 'all'; void load(); }}
                    title={$_('collection.tag_mode_toggle_title')}
                >{tagMode === 'all' ? $_('collection.tag_mode_all') : $_('collection.tag_mode_any')}</button>
            {/if}
            {#if activeTagIds.length}
                <button type="button" class="tag-clear" onclick={() => { activeTagIds = []; void load(); }}>{$_('collection.tag_filter_clear')}</button>
            {/if}
        </div>
    {/if}

    {#if canEdit}
        <div class="bulk-toolbar">
            <span class="muted">{$_('collection.selected_count', { values: { count: selectedItemIds.length } })}</span>
            <button type="button" class="secondary" onclick={selectVisibleItems} disabled={!items.length || bulkBusy}>{$_('collection.select_visible')}</button>
            <button type="button" class="secondary" onclick={clearSelection} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.clear_selection')}</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ depleted: true })} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_depleted')}</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ depleted: false })} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_in_stock')}</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ wanted: true })} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_wanted')}</button>
            <button type="button" class="secondary" onclick={() => bulkPatch({ wanted: false })} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_owned')}</button>
            <button type="button" class="secondary" onclick={bulkArchive} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_archive')}</button>
            <button type="button" class="secondary" onclick={bulkRestore} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_restore')}</button>
            <select bind:value={selectedBulkTagId} disabled={bulkBusy || tags.length === 0} title="Tag for bulk tagging">
                <option value="">{$_('collection.tag_dropdown')}</option>
                {#each tags as t (t.id)}
                    <option value={t.id}>{t.name}</option>
                {/each}
            </select>
            <button type="button" class="secondary" onclick={() => bulkTag('add')} disabled={!selectedItemIds.length || !selectedBulkTagId || bulkBusy}>{$_('collection.bulk_add_tag')}</button>
            <button type="button" class="secondary" onclick={() => bulkTag('remove')} disabled={!selectedItemIds.length || !selectedBulkTagId || bulkBusy}>{$_('collection.bulk_remove_tag')}</button>
            <select bind:value={bulkMoveLocationId} disabled={bulkBusy || locationOptions.length === 0} title="Bulk location move">
                <option value="">{$_('collection.location_dropdown')}</option>
                {#each locationOptions as opt (opt.id)}
                    <option value={opt.id}>{opt.label}</option>
                {/each}
            </select>
            <button type="button" class="secondary" onclick={() => runBulkMoveLocation(false)} disabled={!selectedItemIds.length || !bulkMoveLocationId || bulkBusy}>{$_('collection.bulk_move_location')}</button>
            <button type="button" class="secondary" onclick={() => runBulkMoveLocation(true)} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_clear_location')}</button>
            <select bind:value={selectedBulkContactId} disabled={bulkBusy || contacts.length === 0} title="Contact for bulk lend">
                <option value="">{$_('collection.contact_dropdown')}</option>
                {#each contacts as c (c.id)}
                    <option value={c.id}>{c.name}</option>
                {/each}
            </select>
            <input type="datetime-local" bind:value={bulkLoanDueAt} title="Bulk lend due date" />
            <button type="button" class="secondary" onclick={bulkLend} disabled={!selectedItemIds.length || !selectedBulkContactId || bulkBusy}>{$_('collection.bulk_lend')}</button>
            <button type="button" class="danger" onclick={bulkDelete} disabled={!selectedItemIds.length || bulkBusy}>{$_('collection.bulk_delete')}</button>
        </div>
    {/if}

    {#if loading}
        <p class="muted">{$_('common.loading')}</p>
    {:else if items.length === 0}
        <p class="muted">{$_('collection.no_items')}</p>
    {:else if viewMode === 'grid'}
        <div class="item-grid">
            {#each items as i (i.id)}
                {#if editingId === i.id}
                    <div class="item-card item-card-edit">
                        <div class="item-card-body">
                            {#if collectionCreatorLabel}
                                <input bind:value={editCreator} placeholder={collectionCreatorLabel} class="edit-input" list="creator-suggestions" />
                            {/if}
                            <input bind:value={editTitle} placeholder={$_('collection.col_title')} class="edit-input" />
                            {#if showCollectionSubtitle}
                                <input bind:value={editSubtitle} placeholder={$_('collection.subtitle_placeholder')} class="edit-input" />
                            {/if}
                            <input bind:value={editCondition} placeholder={$_('collection.col_condition')} class="edit-input" list="condition-suggestions" />
                            <input type="number" bind:value={editQuantity} min="0" placeholder={$_('collection.col_qty')} class="edit-input" style="width:5rem" />
                            {#if isConsumable(i.category_slug)}
                                <input type="datetime-local" bind:value={editPurchasedAt} placeholder={$_('collection.consumable_purchased')} class="edit-input" title="Purchased date" />
                                <input type="datetime-local" bind:value={editUseByDate} placeholder={$_('collection.consumable_use_by')} class="edit-input" title="Use by date" />
                                <input type="datetime-local" bind:value={editDateFrozen} placeholder={$_('collection.consumable_frozen')} class="edit-input" title="Date frozen" />
                                <input type="datetime-local" bind:value={editDateOpened} placeholder={$_('collection.consumable_opened')} class="edit-input" title="Date opened" />
                            {/if}
                        </div>
                        <div class="item-card-actions">
                            <button onclick={saveEdit}>{$_('common.save')}</button>
                            <button type="button" class="secondary" onclick={cancelEdit}>{$_('common.cancel')}</button>
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
                                    {$_('collection.item_select_label')}
                                </label>
                            {/if}
                            {#if !isFocused && i.category_slug}
                                <button type="button" class="category-badge filter-link" onclick={() => filterByCategory(i.category_slug!)}>{i.category_slug.split('.').at(-1) ?? i.category_slug}</button>
                            {/if}
                            {#if i.attrs?.creator}
                                <p class="item-creator"><button type="button" class="filter-link" onclick={() => filterBySearch(String(i.attrs!.creator))}>{String(i.attrs.creator)}</button></p>
                            {/if}
                            <p class="item-title">{i.title}</p>
                            {#if i.subtitle}
                                <p class="item-subtitle">{i.subtitle}</p>
                            {/if}
                            <PhotoGallery itemId={i.id} canEdit={canEdit} compact />
                            <ItemComments itemId={i.id} currentUserId={$me?.id} canManage={canEdit} />
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
                                {#if i.condition}<button type="button" class="filter-link" onclick={() => filterBySearch(i.condition!)}>{i.condition}</button>{/if}
                                {#if i.quantity > 1}<span>×{i.quantity}</span>{/if}
                                {#if displayValue(i) != null}<span>{formatValue(i)}</span>{/if}
                                {#if i.location_path && i.location_path.length}<button type="button" class="location-badge filter-link" title="Filter by location" onclick={() => filterBySearch(i.location_path!.at(-1)!)}>{i.location_path.join(' / ')}</button>{/if}
                                {#if i.depleted}<span class="depleted-badge">{$_('collection.badge_depleted')}</span>{/if}
                                {#if i.wanted}<span class="wanted-badge">{$_('collection.badge_wanted')}</span>{/if}
                                {#if i.archived_at}<span class="archived-badge">{$_('collection.badge_archived')}</span>{/if}
                                {#if i.flagged_at}
                                    <span class="flagged-badge" title={i.flagged_note ?? $_('collection.flag_for_review')}>
                                        {$_('collection.badge_flagged')}
                                    </span>
                                {/if}
                                {#if isConsumable(i.category_slug)}
                                    {#if i.use_by_date}<span class="date-badge use-by">{$_('collection.badge_use_by', { values: { date: new Date(i.use_by_date).toLocaleDateString() } })}</span>{/if}
                                    {#if i.date_opened}<span class="date-badge opened">{$_('collection.badge_opened', { values: { date: new Date(i.date_opened).toLocaleDateString() } })}</span>{/if}
                                {/if}
                            </div>
                        </div>
                        {#if canEdit}
                            <div class="item-card-actions">
                                <button type="button" class="secondary" onclick={() => startEdit(i)}>{$_('collection.item_edit')}</button>
                                {#if quickActionFor(i.category_slug)}
                                    <button type="button" class="secondary" onclick={() => triggerQuickAction(i)} disabled={i.archived_at != null}>{quickActionFor(i.category_slug)!.label()}</button>
                                {/if}
                                <button type="button" class="secondary" onclick={() => duplicateItem(i)} disabled={i.archived_at != null}>{$_('collection.item_duplicate')}</button>
                                <button
                                    type="button"
                                    class={i.depleted ? 'secondary' : 'warn'}
                                    onclick={() => toggleDepleted(i)}
                                    disabled={i.archived_at != null}
                                >{i.depleted ? $_('collection.item_in_stock') : $_('collection.item_depleted')}</button>
                                <button
                                    type="button"
                                    class={i.wanted ? 'secondary' : 'warn'}
                                    onclick={() => toggleWanted(i)}
                                    disabled={i.archived_at != null}
                                >{i.wanted ? $_('collection.item_owned') : $_('collection.item_wanted')}</button>
                                <button
                                    type="button"
                                    class="secondary"
                                    onclick={() => (i.flagged_at ? clearFlag(i) : requestFlagItem(i))}
                                    disabled={i.archived_at != null}
                                >{i.flagged_at ? $_('collection.item_unflag') : $_('collection.item_flag')}</button>
                                <button type="button" class="secondary" onclick={() => (i.archived_at ? restoreArchivedItem(i) : requestArchiveItem(i))}>{i.archived_at ? $_('collection.item_restore') : $_('collection.item_archive')}</button>
                                <button class="danger item-card-delete" onclick={() => requestRemoveItem(i)}>{$_('collection.item_delete')}</button>
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
                    {#if !isFocused}<th>{$_('collection.col_category')}</th>{/if}
                    {#if collectionCreatorLabel}<th>{collectionCreatorLabel}</th>{/if}
                    <th>{$_('collection.col_title')}</th>
                    {#if showCollectionSubtitle}<th>{$_('collection.subtitle_placeholder')}</th>{/if}
                    <th>{$_('collection.col_qty')}</th>
                    <th>{$_('collection.col_condition')}</th>
                    <th>{$_('collection.col_value')}</th>
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
                            <td><input bind:value={editTitle} placeholder={$_('collection.col_title')} class="edit-input" /></td>
                            {#if showCollectionSubtitle}
                                <td><input bind:value={editSubtitle} placeholder={$_('collection.subtitle_placeholder')} class="edit-input" /></td>
                            {/if}
                            <td><input type="number" bind:value={editQuantity} min="0" placeholder={$_('collection.col_qty')} class="edit-input qty-input" /></td>
                            <td><input bind:value={editCondition} placeholder={$_('collection.col_condition')} class="edit-input" list="condition-suggestions" /></td>
                            <td class="muted">{formatValue(i)}</td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button onclick={saveEdit}>{$_('common.save')}</button>
                                    <button type="button" class="secondary" onclick={cancelEdit}>{$_('common.cancel')}</button>
                                </td>
                            {/if}
                        </tr>
                        {#if isConsumable(i.category_slug)}
                            <tr class="editing-row consumable-dates-row">
                                <td colspan="100" style="padding: 0.5rem;">
                                    <div class="consumable-dates-grid">
                                        <input type="datetime-local" bind:value={editPurchasedAt} placeholder={$_('collection.consumable_purchased')} class="edit-input" title="Purchased date" />
                                        <input type="datetime-local" bind:value={editUseByDate} placeholder={$_('collection.consumable_use_by')} class="edit-input" title="Use by date" />
                                        <input type="datetime-local" bind:value={editDateFrozen} placeholder={$_('collection.consumable_frozen')} class="edit-input" title="Date frozen" />
                                        <input type="datetime-local" bind:value={editDateOpened} placeholder={$_('collection.consumable_opened')} class="edit-input" title="Date opened" />
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
                            {#if !isFocused}<td class="muted"><button type="button" class="filter-link" onclick={() => i.category_slug && filterByCategory(i.category_slug)}>{i.category_slug ?? ''}</button></td>{/if}
                            {#if collectionCreatorLabel}<td class="muted"><button type="button" class="filter-link" onclick={() => filterBySearch(String(i.attrs?.creator ?? ''))}>{String(i.attrs?.creator ?? '')}</button></td>{/if}
                            <td>
                                {i.title}
                                {#if i.subtitle && !showCollectionSubtitle}<span class="muted"> · {i.subtitle}</span>{/if}
                                {#if i.flagged_at}
                                    <span class="flagged-inline" title={i.flagged_note ?? $_('collection.flag_for_review')}>{$_('collection.badge_flagged')}</span>
                                {/if}
                                {#if i.wanted}
                                    <span class="wanted-inline" title="Marked as wanted / not currently owned">{$_('collection.badge_wanted')}</span>
                                {/if}
                                {#if i.archived_at}
                                    <span class="archived-inline" title={i.disposition_type ?? 'archived'}>{$_('collection.badge_archived')}</span>
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
                                <PhotoGallery itemId={i.id} canEdit={canEdit} compact />
                                <ItemComments itemId={i.id} currentUserId={$me?.id} canManage={canEdit} />
                            </td>
                            {#if showCollectionSubtitle}<td class="muted">{i.subtitle ?? ''}</td>{/if}
                            <td>{i.quantity}</td>
                            <td>{i.condition ?? ''}</td>
                            <td class="muted">{formatValue(i)}</td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button class="secondary" onclick={() => startEdit(i)}>{$_('collection.item_edit')}</button>
                                    {#if quickActionFor(i.category_slug)}
                                        <button class="secondary" onclick={() => triggerQuickAction(i)} disabled={i.archived_at != null}>{quickActionFor(i.category_slug)!.label()}</button>
                                    {/if}
                                    <button class="secondary" onclick={() => duplicateItem(i)} disabled={i.archived_at != null}>{$_('collection.item_duplicate')}</button>
                                    <button
                                        type="button"
                                        class={i.depleted ? 'secondary' : 'warn'}
                                        onclick={() => toggleDepleted(i)}
                                        disabled={i.archived_at != null}
                                        title={i.depleted ? $_('collection.item_in_stock') : $_('collection.item_depleted')}
                                    >{i.depleted ? $_('collection.item_in_stock') : $_('collection.item_depleted')}</button>
                                    <button
                                        type="button"
                                        class={i.wanted ? 'secondary' : 'warn'}
                                        onclick={() => toggleWanted(i)}
                                        disabled={i.archived_at != null}
                                        title={i.wanted ? $_('collection.item_owned') : $_('collection.item_wanted')}
                                    >{i.wanted ? $_('collection.item_owned') : $_('collection.item_wanted')}</button>
                                    <button
                                        type="button"
                                        class="secondary"
                                        onclick={() => (i.flagged_at ? clearFlag(i) : requestFlagItem(i))}
                                        disabled={i.archived_at != null}
                                    >{i.flagged_at ? $_('collection.item_unflag') : $_('collection.item_flag')}</button>
                                    <button type="button" class="secondary" onclick={() => (i.archived_at ? restoreArchivedItem(i) : requestArchiveItem(i))}>{i.archived_at ? $_('collection.item_restore') : $_('collection.item_archive')}</button>
                                    <button class="danger" onclick={() => requestRemoveItem(i)}>{$_('collection.item_delete')}</button>
                                </td>
                            {/if}
                        </tr>
                    {/if}
                {/each}
            </tbody>
        </table>
    {/if}
{:else if !loading}
    <p class="error">{$_('collection.not_found')}</p>
{/if}

{#if confirmDialog === 'delete-item'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-item-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-item-title">{$_('collection.delete_item_title')}</h3>
            <p class="muted">{$_('collection.delete_item_text', { values: { title: pendingDeleteItemTitle || 'This item' } })}</p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>{$_('common.cancel')}</button>
                <button type="button" class="danger" onclick={removeItemConfirmed}>{$_('common.delete')}</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'delete-collection'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-collection-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-collection-title">{$_('collection.delete_collection_title')}</h3>
            <p class="muted">
                {$_('collection.delete_collection_text', { values: { name: collection?.name ?? '' } })}
            </p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>{$_('common.cancel')}</button>
                <button type="button" class="danger" onclick={deleteCollectionConfirmed}>{$_('collection.delete_collection_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'flag-item'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="flag-item-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="flag-item-title">{$_('collection.flag_title')}</h3>
            <p class="muted">{$_('collection.flag_text', { values: { title: pendingFlagItemTitle || 'This item' } })}</p>
            <label>
                {$_('collection.flag_note_label')}
                <input bind:value={flagNoteInput} maxlength="256" placeholder={$_('collection.flag_note_placeholder')} />
            </label>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>{$_('common.cancel')}</button>
                <button type="button" onclick={flagItemConfirmed}>{$_('collection.flag_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'mark-owned'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="mark-owned-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="mark-owned-title">{$_('collection.mark_owned_title')}</h3>
            <p class="muted">{$_('collection.mark_owned_text', { values: { title: pendingOwnedItemTitle || 'this item' } })}</p>
            <label>
                {$_('collection.mark_owned_date_label')}
                <input type="datetime-local" bind:value={ownedAtInput} />
            </label>
            <label>
                {$_('collection.mark_owned_price_label')}
                <input type="number" min="0" step="0.01" bind:value={ownedPriceInput} placeholder={$_('collection.mark_owned_price_placeholder')} />
            </label>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>{$_('common.cancel')}</button>
                <button type="button" onclick={markOwnedConfirmed}>{$_('collection.mark_owned_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

{#if confirmDialog === 'archive-item'}
    <div class="modal-backdrop" role="presentation" onclick={() => (confirmDialog = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="archive-item-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="archive-item-title">{$_('collection.archive_title')}</h3>
            <p class="muted">{$_('collection.archive_text', { values: { title: pendingArchiveItemTitle || 'this item' } })}</p>
            <label>
                {$_('collection.archive_disposition_label')}
                <select bind:value={archiveDispositionType}>
                    <option value="archived">{$_('collection.archive_archived')}</option>
                    <option value="sold">{$_('collection.archive_sold')}</option>
                    <option value="disposed">{$_('collection.archive_disposed')}</option>
                    <option value="donated">{$_('collection.archive_donated')}</option>
                </select>
            </label>
            <label>
                {$_('collection.archive_date_label')}
                <input type="datetime-local" bind:value={archiveDispositionAt} />
            </label>
            <label>
                {$_('collection.archive_amount_label')}
                <input type="number" min="0" step="0.01" bind:value={archiveDispositionAmount} placeholder={$_('collection.archive_amount_placeholder')} />
            </label>
            <label>
                {$_('collection.archive_buyer_label')}
                <input bind:value={archiveDispositionBuyer} maxlength="256" placeholder={$_('collection.archive_buyer_placeholder')} />
            </label>
            <label>
                {$_('collection.archive_note_label')}
                <input bind:value={archiveDispositionNote} maxlength="512" placeholder={$_('collection.archive_note_placeholder')} />
            </label>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (confirmDialog = null)}>{$_('common.cancel')}</button>
                <button type="button" onclick={archiveItemConfirmed}>{$_('collection.archive_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

<!-- Type-ahead datalists for inline edit -->
<datalist id="condition-suggestions">
    <option value="New" />
    <option value="Mint" />
    <option value="Excellent" />
    <option value="Good" />
    <option value="Fair" />
    <option value="Poor" />
    {#each conditionSuggestions as s (s)}<option value={s} />{/each}
</datalist>
<datalist id="creator-suggestions">
    {#each creatorSuggestions as s (s)}<option value={s} />{/each}
</datalist>

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
    .filter-link {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        cursor: pointer;
        color: inherit;
        text-align: left;
    }
    .filter-link {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        cursor: pointer;
        color: inherit;
        text-align: left;
    }
    .filter-link:hover { text-decoration: underline; opacity: 0.8; }
    .tag-filters {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        margin-top: 0.25rem;
        margin-bottom: 0.25rem;
    }
    .tag-chip {
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        border: 1px solid var(--border-color, #ccc);
        background: none;
        font-size: 0.8rem;
        cursor: pointer;
        color: var(--text-muted, #555);
        transition: background 0.1s, color 0.1s;
    }
    .tag-chip.active {
        background: var(--accent, #5b8af5);
        color: #fff;
        border-color: var(--accent, #5b8af5);
    }
    .tag-mode-toggle {
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        border: 1px solid var(--accent, #5b8af5);
        background: none;
        font-size: 0.75rem;
        font-weight: 600;
        cursor: pointer;
        color: var(--accent, #5b8af5);
    }
    .tag-clear {
        background: none;
        border: none;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
        cursor: pointer;
        text-decoration: underline;
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
