<script lang="ts">
    import { onMount, tick, untrack } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Category, type Collection, type Contact, type Item, type ItemTemplate, type LocationNode, type Tag } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';
    import { Button, ConfirmDialog } from '$lib/components';
    import { me } from '$lib/session';
    import AddItemCard from './AddItemCard.svelte';
    import FilterBar from './FilterBar.svelte';
    import BulkToolbar from './BulkToolbar.svelte';
    import ItemGrid from './ItemGrid.svelte';
    import ItemTable from './ItemTable.svelte';
    import ItemEditPanel from './ItemEditPanel.svelte';
    import DeleteItemDialog from './modals/DeleteItemDialog.svelte';
    import MarkOwnedDialog from './modals/MarkOwnedDialog.svelte';
    import ArchiveItemDialog from './modals/ArchiveItemDialog.svelte';
    import FlagItemDialog from './modals/FlagItemDialog.svelte';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let templates = $state<ItemTemplate[]>([]);
    let tags = $state<Tag[]>([]);
    let contacts = $state<Contact[]>([]);
    let relatedItemTitles = $state<Record<string, string>>({});
    let categories = $state<Category[]>([]);
    let search = $state('');
    let rootFilter = $state('');
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

    // Slide-over edit panel
    let editPanelItem = $state<Item | null>(null);

    // Item action dialog state
    let confirmDialog = $state<'delete-item' | 'flag-item' | 'mark-owned' | 'archive-item' | null>(null);
    let pendingDeleteItemId = $state<string | null>(null);
    let pendingDeleteItemTitle = $state('');
    let pendingFlagItemId = $state<string | null>(null);
    let pendingFlagItemTitle = $state('');
    let pendingFlagItemNote = $state('');
    let pendingOwnedItemId = $state<string | null>(null);
    let pendingOwnedItemTitle = $state('');
    let pendingArchiveItemId = $state<string | null>(null);
    let pendingArchiveItemTitle = $state('');

    // Bulk action state
    let bulkBusy = $state(false);
    let selectedBulkTagId = $state('');
    let bulkMoveLocationId = $state('');
    let locations = $state<LocationNode[]>([]);
    let selectedBulkContactId = $state('');
    let bulkLoanDueAt = $state('');

    // Create form
    let newRoot = $state('other');
    let newLeaf = $state('other.generic');
    let newQuery = $state('');
    let newCreator = $state('');
    let newSubtitle = $state('');
    let newAttrs = $state<Record<string, unknown>>({});
    let scraping = $state(false);

    let searchInputEl: HTMLInputElement | undefined = $state();
    let addCardRef: { focusTitle?: () => void } | undefined = $state();

    const activeTemplate = $derived(templates.find(t => t.category_slug === newLeaf) ?? null);

    // Fallback labels shown only when no matching template exists for the active leaf
    const creatorLabel = $derived.by(() => {
        if (activeTemplate) return null;
        if (newLeaf.startsWith('music.')) return $_('collection.creator_artist');
        if (newLeaf.startsWith('books.')) return $_('collection.creator_author');
        if (newLeaf.startsWith('movies.')) return $_('collection.creator_director');
        if (newLeaf.startsWith('games.')) return $_('collection.creator_developer');
        if (newLeaf.startsWith('tabletop.')) return $_('collection.creator_designer');
        return null;
    });
    const subtitleLabel = $derived.by(() => {
        if (activeTemplate) return null;
        if (newLeaf.startsWith('books.') || newLeaf.startsWith('movies.') || newLeaf.startsWith('games.'))
            return $_('collection.subtitle_placeholder');
        return null;
    });

    function isConsumable(slug: string | null): boolean {
        if (!slug) return false;
        const root = slug.split('.')[0];
        return ['spices', 'fuel_chemicals', 'batteries'].includes(root);
    }

    const collectionIsConsumable = $derived(
        isConsumable(collection?.default_category_slug ?? null)
    );

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

    function quickActionLabel(slug: string | null): (() => string) | null {
        return quickActionFor(slug)?.label ?? null;
    }

    const cid = $derived(page.params.id ?? '');
    // Generation counter: incremented on every tab switch so stale async loads are discarded.
    // Plain variable (not $state) so reading/writing it inside $effect creates no reactive dependency.
    let loadGen = 0;
    const roots = $derived(rootCategories(categories));
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );
    const locationOptions = $derived.by(() => {
        const out: { id: string; label: string }[] = [];
        const walk = (nodes: LocationNode[], depth: number) => {
            for (const n of nodes) {
                out.push({ id: n.id, label: `${'  '.repeat(depth)}${n.name}` });
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
    const isFocused = $derived.by(() => {
        const def = collection?.default_category_slug;
        if (!def) return false;
        const c = categories.find((x) => x.slug === def);
        return !!c;
    });
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
        if (leaves.length && !leaves.some((l) => l.slug === untrack(() => newLeaf))) {
            newLeaf = leaves[0].slug;
        }
    });

    function detectKind(q: string): 'url' | 'isbn' | 'ean' | 'title' {
        const s = q.trim();
        if (/^https?:\/\//i.test(s)) return 'url';
        const digits = s.replace(/[\s-]/g, '');
        if (/^(?:97[89])\d{10}$/.test(digits)) return 'isbn';
        if (/^\d{9}[\dXx]$/.test(digits)) return 'isbn';
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

    function toggleSelected(itemId: string) {
        if (selectedItemIds.includes(itemId)) {
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
        const snapCid = cid;
        const snapGen = loadGen;
        loading = true;
        try {
            if (categories.length === 0) categories = await loadCategories();
            if (snapGen !== loadGen) return;
            collection = await api.get<Collection>(`/collections/${snapCid}`);
            if (snapGen !== loadGen) return;
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
            const params = new URLSearchParams({ collection_id: snapCid });
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
                api.get<ItemTemplate[]>(`/collections/${snapCid}/templates`),
                api.get<Tag[]>('/tags'),
                api.get<Contact[]>('/contacts'),
                api.get<LocationNode[]>(`/locations?collection_id=${snapCid}`),
            ]);
            // Discard if a newer load has already started (tab was switched mid-flight).
            if (snapGen !== loadGen) return;
            items = fetchedItems;
            templates = fetchedTemplates;
            tags = fetchedTags;
            contacts = fetchedContacts;
            locations = fetchedLocations;
            // If no default_category_slug was set, seed the Add form from the
            // most-used category among the collection's current items.
            if (!didSeedDefaults && fetchedItems.length > 0) {
                const freq: Record<string, number> = {};
                for (const item of fetchedItems) {
                    if (item.category_slug) freq[item.category_slug] = (freq[item.category_slug] ?? 0) + 1;
                }
                const topEntry = Object.entries(freq).sort((a, b) => b[1] - a[1])[0];
                const topSlug = topEntry?.[0];
                if (topSlug) {
                    const cat = categories.find((c) => c.slug === topSlug);
                    if (cat) {
                        if (cat.parent_id === null) {
                            newRoot = cat.slug;
                        } else {
                            const parent = categories.find((c) => c.id === cat.parent_id);
                            if (parent) newRoot = parent.slug;
                            newLeaf = cat.slug;
                        }
                    }
                }
                didSeedDefaults = true;
            }
            await hydrateRelatedItemTitles(items);
        } catch (e) {
            if (snapGen === loadGen) error = (e as Error).message;
        } finally {
            if (snapGen === loadGen) loading = false;
        }
    }

    async function bulkPatch(payload: Record<string, unknown>) {
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
        // Merge template attrs, dropping empty values
        const attrs: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(newAttrs)) {
            if (v !== '' && v !== null && v !== undefined) attrs[k] = v;
        }
        // Fallback creator field when no template is active for this category
        if (!activeTemplate && newCreator.trim()) attrs.creator = newCreator.trim();
        await api.post('/items', {
            collection_id: cid,
            category: newLeaf,
            title,
            subtitle: newSubtitle.trim() || undefined,
            attrs: Object.keys(attrs).length ? attrs : undefined,
            template_id: activeTemplate?.id ?? undefined,
            identifiers
        });
        newQuery = '';
        newCreator = '';
        newSubtitle = '';
        newAttrs = {};
        await load();
        await tick();
        addCardRef?.focusTitle?.();
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

    async function saveEditFromPanel(id: string, payload: Record<string, unknown>) {
        await api.patch(`/items/${id}`, payload);
        editPanelItem = null;
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
            confirmDialog = 'mark-owned';
            return;
        }
        await api.patch(`/items/${item.id}`, { wanted: true });
        await load();
    }

    async function markOwnedConfirmed(ownedAt: string, ownedPrice: string) {
        if (!pendingOwnedItemId) return;
        const payload: Record<string, unknown> = { wanted: false };
        if (ownedAt) payload.acquired_at = new Date(ownedAt).toISOString();
        if (ownedPrice.trim()) payload.purchase_price = Number(ownedPrice);
        await api.patch(`/items/${pendingOwnedItemId}`, payload);
        pendingOwnedItemId = null;
        pendingOwnedItemTitle = '';
        confirmDialog = null;
        await load();
    }

    function requestFlagItem(item: Item) {
        pendingFlagItemId = item.id;
        pendingFlagItemTitle = item.title;
        pendingFlagItemNote = item.flagged_note ?? '';
        confirmDialog = 'flag-item';
    }

    async function flagItemConfirmed(note: string) {
        if (!pendingFlagItemId) return;
        await api.post(`/items/${pendingFlagItemId}/flag`, { note });
        pendingFlagItemId = null;
        pendingFlagItemTitle = '';
        pendingFlagItemNote = '';
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
        confirmDialog = 'archive-item';
    }

    async function archiveItemConfirmed(payload: { disposition_type: string; disposition_at?: string; disposition_buyer?: string; disposition_note?: string; disposition_amount?: number }) {
        if (!pendingArchiveItemId) return;
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

    onMount(() => {
        viewMode = (localStorage.getItem('tangible:viewMode') ?? 'list') as 'list' | 'grid';
        const onGlobalKeydown = (event: KeyboardEvent) => {
            if (event.key !== '/') return;
            if (event.metaKey || event.ctrlKey || event.altKey) return;
            const active = document.activeElement;
            if (active instanceof HTMLInputElement || active instanceof HTMLTextAreaElement) return;
            event.preventDefault();
            searchInputEl?.focus();
            searchInputEl?.select();
        };
        window.addEventListener('keydown', onGlobalKeydown);
        return () => window.removeEventListener('keydown', onGlobalKeydown);
    });

    // Reload everything when the route's collection id changes (tab switch).
    // SvelteKit reuses the component across [id] changes, so onMount runs only once.
    $effect(() => {
        if (!cid) return;
        // Bump generation first so any in-flight load() for the previous cid
        // discards its results when it eventually resolves.
        loadGen += 1;
        // Reset per-collection state so the previous tab's data doesn't flash.
        items = [];
        templates = [];
        locations = [];
        selectedItemIds = [];
        editPanelItem = null;
        // Reset filter/sort state so it doesn't carry over to a different collection.
        search = '';
        rootFilter = '';
        activeTagIds = [];
        wantedFilter = 'all';
        archivedFilter = 'active';
        didSeedDefaults = false;
        loading = true;
        untrack(() => void load());
    });

    function filterBySearch(value: string) {
        search = value;
        void load();
    }

    function filterByCategory(slug: string) {
        rootFilter = slug;
        void load();
    }

    $effect(() => {
        localStorage.setItem('tangible:viewMode', viewMode);
    });

    // SSE real-time updates: reconcile item list without a full reload.
    $effect(() => {
        if (!cid) return;
        const evtSource = new EventSource(`/api/collections/${cid}/events`, { withCredentials: true });
        evtSource.onmessage = (e: MessageEvent) => {
            try {
                const evt = JSON.parse(e.data) as { type: string; id?: string; title?: string };
                if (evt.type === 'item-added') {
                    // Reload to get the full item with all fields.
                    void load();
                } else if (evt.type === 'item-updated' && evt.id) {
                    // Fetch just the updated item and patch it in-place.
                    api.get<Item>(`/items/${evt.id}`).then((updated) => {
                        const idx = items.findIndex((i) => i.id === updated.id);
                        if (idx !== -1) items[idx] = updated;
                    }).catch(() => { /* silent */ });
                } else if (evt.type === 'item-deleted' && evt.id) {
                    items = items.filter((i) => i.id !== evt.id);
                }
                // comment-added: no item-list change needed
            } catch {
                // Malformed event — ignore.
            }
        };
        evtSource.onerror = () => {
            // Browser will auto-reconnect after the retry interval set by server.
        };
        return () => evtSource.close();
    });
</script>

{#if collection}
    {#if canEdit}
        <AddItemCard
            bind:this={addCardRef}
            {creatorLabel}
            {subtitleLabel}
            {activeTemplate}
            {newAttrs}
            bind:newRoot
            bind:newLeaf
            bind:newQuery
            bind:newCreator
            bind:newSubtitle
            {scraping}
            {error}
            {detected}
            onSubmit={addItem}
            onLookup={lookupAndPrefill}
            onBarcodeChange={onBarcodeImagePicked}
        />
    {/if}

    <FilterBar
        bind:search
        bind:viewMode
        bind:sortBy
        bind:sortDir
        bind:sortAttr
        bind:searchInputEl
        {isFocused}
        {roots}
        bind:rootFilter
        bind:wantedFilter
        bind:archivedFilter
        {tags}
        bind:activeTagIds
        bind:tagMode
        onchange={() => load()}
    />

    {#if canEdit}
        <BulkToolbar
            selectedCount={selectedItemIds.length}
            busy={bulkBusy}
            {tags}
            {locationOptions}
            {contacts}
            bind:selectedBulkTagId
            bind:bulkMoveLocationId
            bind:selectedBulkContactId
            bind:bulkLoanDueAt
            onSelectAll={selectVisibleItems}
            onClearSelection={clearSelection}
            onBulkDepleted={() => bulkPatch({ depleted: true })}
            onBulkInStock={() => bulkPatch({ depleted: false })}
            onBulkWanted={() => bulkPatch({ wanted: true })}
            onBulkOwned={() => bulkPatch({ wanted: false })}
            onBulkArchive={bulkArchive}
            onBulkRestore={bulkRestore}
            onBulkAddTag={() => bulkTag('add')}
            onBulkRemoveTag={() => bulkTag('remove')}
            onBulkMoveLocation={() => runBulkMoveLocation(false)}
            onBulkClearLocation={() => runBulkMoveLocation(true)}
            onBulkLend={bulkLend}
            onBulkDelete={bulkDelete}
        />
    {/if}

    {#if loading}
        <p class="muted">{$_('common.loading')}</p>
    {:else if items.length === 0}
        <p class="muted">{$_('collection.no_items')}</p>
    {:else if viewMode === 'grid'}
        <ItemGrid
            {items}
            {canEdit}
            {isFocused}
            {selectedItemIds}
            {collectionCreatorLabel}
            currentUserId={$me?.id}
            {formatValue}
            {displayValue}
            {relationEntries}
            {relationTitle}
            {quickActionLabel}
            {isConsumable}
            onToggleSelect={toggleSelected}
            onEdit={(item) => { editPanelItem = item; }}
            onQuickAction={triggerQuickAction}
            onDuplicate={duplicateItem}
            onToggleDepleted={toggleDepleted}
            onToggleWanted={toggleWanted}
            onToggleFlag={(item) => (item.flagged_at ? clearFlag(item) : requestFlagItem(item))}
            onArchive={(item) => (item.archived_at ? restoreArchivedItem(item) : requestArchiveItem(item))}
            onDelete={requestRemoveItem}
            onFilterByCategory={filterByCategory}
            onFilterBySearch={filterBySearch}
        />
    {:else}
        <ItemTable
            {items}
            {canEdit}
            {isFocused}
            {collectionIsConsumable}
            {selectedItemIds}
            {collectionCreatorLabel}
            {showCollectionSubtitle}
            {formatValue}
            {relationEntries}
            {relationTitle}
            {quickActionLabel}
            {isConsumable}
            onSelectAll={(checked) => (checked ? selectVisibleItems() : clearSelection())}
            onToggleSelect={toggleSelected}
            onEdit={(item) => { editPanelItem = item; }}
            onQuickAction={triggerQuickAction}
            onDuplicate={duplicateItem}
            onToggleDepleted={toggleDepleted}
            onToggleWanted={toggleWanted}
            onToggleFlag={(item) => (item.flagged_at ? clearFlag(item) : requestFlagItem(item))}
            onArchive={(item) => (item.archived_at ? restoreArchivedItem(item) : requestArchiveItem(item))}
            onDelete={requestRemoveItem}
            onFilterByCategory={filterByCategory}
            onFilterBySearch={filterBySearch}
        />
    {/if}


{:else if !loading}
    <p class="error">{$_('collection.not_found')}</p>
{/if}

<ItemEditPanel
    item={editPanelItem}
    {cid}
    {collectionCreatorLabel}
    {showCollectionSubtitle}
    {isConsumable}
    {categories}
    onSave={saveEditFromPanel}
    onClose={() => { editPanelItem = null; }}
/>

<DeleteItemDialog
    open={confirmDialog === 'delete-item'}
    itemTitle={pendingDeleteItemTitle}
    onconfirm={removeItemConfirmed}
    oncancel={() => { confirmDialog = null; }}
/>

<FlagItemDialog
    open={confirmDialog === 'flag-item'}
    itemTitle={pendingFlagItemTitle}
    initialNote={pendingFlagItemNote}
    onconfirm={flagItemConfirmed}
    oncancel={() => { confirmDialog = null; }}
/>

<MarkOwnedDialog
    open={confirmDialog === 'mark-owned'}
    itemTitle={pendingOwnedItemTitle}
    onconfirm={markOwnedConfirmed}
    oncancel={() => { confirmDialog = null; }}
/>

<ArchiveItemDialog
    open={confirmDialog === 'archive-item'}
    itemTitle={pendingArchiveItemTitle}
    onconfirm={archiveItemConfirmed}
    oncancel={() => { confirmDialog = null; }}
/>

<style></style>
