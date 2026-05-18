<script lang="ts">
    import { api } from '$lib/api';
    import { _ } from 'svelte-i18n';
    import { tick } from 'svelte';
    import { GROCERY_CATEGORIES } from '$lib/shoppingCategories';
    import type { ShoppingCategory } from '$lib/shoppingCategories';
    import Icon from '$lib/Icon.svelte';
    import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

    const PRESET_SLUGS = new Set(GROCERY_CATEGORIES.map((c) => c.slug));

    interface Aisle {
        id: string;
        name: string;
        position: number;
        category_slugs: string[];
    }

    interface Store {
        id: string;
        name: string;
        aisles: Aisle[];
    }

    let { onClose = undefined, standalone = false, initialStoreId = null, focusNew = false }: { onClose?: () => void; standalone?: boolean; initialStoreId?: string | null; focusNew?: boolean } = $props();

    let stores = $state<Store[]>([]);
    let selectedStoreId = $state<string | null>(null);
    let loading = $state(true);
    let error = $state('');

    // create-store form
    let newStoreName = $state('');
    let creatingStore = $state(false);
    let showNewStoreForm = $state(false);

    // aisle being created/edited  null = none, object = editing
    let editingAisle = $state<Aisle | null>(null);
    let showNewAisle = $state(false);
    // aisle form state
    let aisleName = $state('');
    let aisleSelectedSlugs = $state<Set<string>>(new Set());
    let aisleCustomSlug = $state('');
    let savingAisle = $state(false);

    const selectedStore = $derived(stores.find((s) => s.id === selectedStoreId) ?? null);
    const sortedAisles = $derived(
        selectedStore ? [...selectedStore.aisles].sort((a, b) => a.position - b.position) : []
    );

    // new-store input ref for focusNew support
    let newStoreInput = $state<HTMLInputElement | null>(null);

    async function load() {
        loading = true;
        try {
            stores = await api.get<Store[]>('/grocery/stores');
            if (initialStoreId && stores.find(s => s.id === initialStoreId)) {
                selectedStoreId = initialStoreId;
            } else if (stores.length && !selectedStoreId) {
                selectedStoreId = stores[0].id;
            }
            if (focusNew) {
                showNewStoreForm = true;
                await tick();
                newStoreInput?.focus();
            }
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function createStore() {
        if (!newStoreName.trim()) return;
        creatingStore = true;
        try {
            const s = await api.post<Store>('/grocery/stores', { name: newStoreName.trim() });
            stores = [...stores, s];
            selectedStoreId = s.id;
            newStoreName = '';
            showNewStoreForm = false;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            creatingStore = false;
        }
    }

    let deleteStoreId = $state<string | null>(null);
    let deleteStoreOpen = $state(false);

    async function deleteStore(id: string) {
        try {
            await api.delete(`/grocery/stores/${id}`);
            stores = stores.filter((s) => s.id !== id);
            if (selectedStoreId === id) selectedStoreId = stores[0]?.id ?? null;
        } catch (e) {
            error = (e as Error).message;
        }
    }

    function openNewAisle() {
        editingAisle = null;
        aisleName = '';
        aisleSelectedSlugs = new Set();
        aisleCustomSlug = '';
        showNewAisle = true;
    }

    function openEditAisle(aisle: Aisle) {
        editingAisle = aisle;
        aisleName = aisle.name;
        const presetSet: Set<string> = new Set();
        const customs: string[] = [];
        for (const s of aisle.category_slugs) {
            if (PRESET_SLUGS.has(s)) presetSet.add(s);
            else customs.push(s);
        }
        aisleSelectedSlugs = presetSet;
        aisleCustomSlug = customs.join(', ');
        showNewAisle = true;
    }

    function toggleSlug(slug: string) {
        const next = new Set(aisleSelectedSlugs);
        if (next.has(slug)) next.delete(slug);
        else next.add(slug);
        aisleSelectedSlugs = next;
    }

    function buildSlugs(): string[] {
        const result = [...aisleSelectedSlugs];
        for (const s of aisleCustomSlug.split(',').map((x) => x.trim().toLowerCase().replace(/\s+/g, '-'))) {
            if (s && !result.includes(s)) result.push(s);
        }
        return result;
    }

    async function saveAisle() {
        if (!aisleName.trim() || !selectedStoreId) return;
        savingAisle = true;
        const slugs = buildSlugs();
        try {
            if (editingAisle) {
                const updated = await api.patch<Aisle>(
                    `/grocery/stores/${selectedStoreId}/aisles/${editingAisle.id}`,
                    { name: aisleName.trim(), category_slugs: slugs }
                );
                stores = stores.map((s) =>
                    s.id === selectedStoreId
                        ? { ...s, aisles: s.aisles.map((a) => (a.id === updated.id ? updated : a)) }
                        : s
                );
            } else {
                const position = sortedAisles.length;
                const created = await api.post<Aisle>(
                    `/grocery/stores/${selectedStoreId}/aisles`,
                    { name: aisleName.trim(), position, category_slugs: slugs }
                );
                stores = stores.map((s) =>
                    s.id === selectedStoreId ? { ...s, aisles: [...s.aisles, created] } : s
                );
            }
            showNewAisle = false;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            savingAisle = false;
        }
    }

    async function deleteAisle(aisleId: string) {
        if (!selectedStoreId) return;
        try {
            await api.delete(`/grocery/stores/${selectedStoreId}/aisles/${aisleId}`);
            stores = stores.map((s) =>
                s.id === selectedStoreId
                    ? { ...s, aisles: s.aisles.filter((a) => a.id !== aisleId) }
                    : s
            );
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function moveAisle(aisleId: string, direction: -1 | 1) {
        if (!selectedStoreId) return;
        const aisles = [...sortedAisles];
        const idx = aisles.findIndex((a) => a.id === aisleId);
        const swapIdx = idx + direction;
        if (swapIdx < 0 || swapIdx >= aisles.length) return;
        [aisles[idx], aisles[swapIdx]] = [aisles[swapIdx], aisles[idx]];
        try {
            await api.put(`/grocery/stores/${selectedStoreId}/aisles/reorder`, {
                aisle_ids: aisles.map((a) => a.id),
            });
            stores = stores.map((s) =>
                s.id === selectedStoreId
                    ? {
                          ...s,
                          aisles: aisles.map((a, i) => ({ ...a, position: i })),
                      }
                    : s
            );
        } catch (e) {
            error = (e as Error).message;
        }
    }

    function categoryLabel(slug: string): string {
        return GROCERY_CATEGORIES.find((c) => c.slug === slug)?.label ?? slug;
    }

    $effect(() => { load(); });
</script>

<div class={standalone ? 'standalone' : 'overlay'} role={standalone ? undefined : 'dialog'} aria-modal={standalone ? undefined : true} aria-label="Store manager">
    <div class="panel">
        <div class="panel-header">
            <h2>{$_('grocery_store.title')}</h2>
            {#if !standalone && onClose}
                <button class="close-btn" type="button" onclick={onClose} aria-label={$_('common.close')}><Icon name="x" size={18} /></button>
            {/if}
        </div>

        {#if error}
            <p class="error">{error}</p>
        {/if}

        {#if loading}
            <p class="muted">{$_('common.loading')}</p>
        {:else}
            <div class="layout">
                <!-- Store sidebar -->
                <div class="store-sidebar">
                    <ul class="store-list">
                        {#each stores as store (store.id)}
                            <li class:active={store.id === selectedStoreId}>
                                <button
                                    type="button"
                                    class="store-name-btn"
                                    onclick={() => { selectedStoreId = store.id; showNewAisle = false; }}
                                >{store.name}</button>
                                <button
                                    type="button"
                                    class="del-btn"
                                    title="Delete store"
                                    onclick={() => { deleteStoreId = store.id; deleteStoreOpen = true; }}
                                ><Icon name="x" size={14} /></button>
                            </li>
                        {/each}
                    </ul>
                    {#if showNewStoreForm}
                    <form class="new-store-form" onsubmit={(e) => { e.preventDefault(); createStore(); }}>
                        <input
                            type="text"
                            bind:this={newStoreInput}
                            bind:value={newStoreName}
                            placeholder={$_('grocery_store.create_store_placeholder')}
                            required
                        />
                        <button type="submit" disabled={creatingStore || !newStoreName.trim()}>
                            {creatingStore ? '…' : '+'}
                        </button>
                        <button type="button" class="cancel-store-btn" onclick={() => { showNewStoreForm = false; newStoreName = ''; }}>
                            <Icon name="x" size={12} />
                        </button>
                    </form>
                {:else}
                    <button type="button" class="new-store-card" onclick={() => { showNewStoreForm = true; }}>
                        <Icon name="plus" size={14} />
                        {$_('grocery_store.new_store_button')}
                    </button>
                {/if}
                </div>

                <!-- Aisle editor -->
                <div class="aisle-editor">
                    {#if !selectedStore}
                        <p class="muted empty-hint">{$_('grocery_store.no_store')}</p>
                    {:else if !showNewAisle}
                        <div class="aisle-header">
                            <span class="aisle-title">{selectedStore.name} — Aisles</span>
                            <button type="button" class="add-aisle-btn" onclick={openNewAisle}>{$_('grocery_store.add_aisle_button')}</button>
                        </div>
                        {#if sortedAisles.length === 0}
                            <p class="muted empty-hint">{$_('grocery_store.no_aisles')}</p>
                        {:else}
                            <ol class="aisle-list">
                                {#each sortedAisles as aisle, idx (aisle.id)}
                                    <li>
                                        <div class="aisle-row">
                                            <div class="aisle-info">
                                                <strong>{aisle.name}</strong>
                                                <div class="slug-chips">
                                                    {#each aisle.category_slugs as slug}
                                                        <span class="slug-chip">{categoryLabel(slug)}</span>
                                                    {/each}
                                                </div>
                                            </div>
                                            <div class="aisle-actions">
                                                <button
                                                    type="button"
                                                    title="Move up"
                                                    aria-label="Move aisle up"
                                                    disabled={idx === 0}
                                                    onclick={() => moveAisle(aisle.id, -1)}
                                                ><Icon name="arrow-up" size={14} /></button>
                                                <button
                                                    type="button"
                                                    title="Move down"
                                                    aria-label="Move aisle down"
                                                    disabled={idx === sortedAisles.length - 1}
                                                    onclick={() => moveAisle(aisle.id, 1)}
                                                ><Icon name="arrow-down" size={14} /></button>
                                                <button type="button" onclick={() => openEditAisle(aisle)}>{$_('common.edit')}</button>
                                                <button
                                                    type="button"
                                                    class="del-btn"
                                                    onclick={() => deleteAisle(aisle.id)}
                                                ><Icon name="x" size={14} /></button>
                                            </div>
                                        </div>
                                    </li>
                                {/each}
                            </ol>
                        {/if}
                    {:else}
                        <!-- Aisle form -->
                        <div class="aisle-form-header">
                            <span class="aisle-title">{editingAisle ? $_('grocery_store.edit_aisle_heading') : $_('grocery_store.new_aisle_heading')}</span>
                            <button type="button" class="text-btn" onclick={() => { showNewAisle = false; }}>{$_('grocery_store.back_button')}</button>
                        </div>
                        <form class="aisle-form" onsubmit={(e) => { e.preventDefault(); saveAisle(); }}>
                            <label>
                                <span>{$_('grocery_store.aisle_name_label')}</span>
                                <input
                                    type="text"
                                    bind:value={aisleName}
                                    placeholder={$_('grocery_store.aisle_name_placeholder')}
                                    required
                                />
                            </label>

                            <fieldset>
                                <legend>{$_('grocery_store.categories_legend')}</legend>
                                <div class="cat-grid">
                                    {#each GROCERY_CATEGORIES as cat (cat.slug)}
                                        <label class="cat-chip-label" class:selected={aisleSelectedSlugs.has(cat.slug)}>
                                            <input
                                                type="checkbox"
                                                checked={aisleSelectedSlugs.has(cat.slug)}
                                                onchange={() => toggleSlug(cat.slug)}
                                            />
                                            {cat.label}
                                        </label>
                                    {/each}
                                </div>
                            </fieldset>

                            <label>
                                <span>{$_('grocery_store.custom_categories_label')} <span class="muted">({$_('grocery_store.custom_categories_hint')})</span></span>
                                <input
                                    type="text"
                                    bind:value={aisleCustomSlug}
                                    placeholder={$_('grocery_store.custom_categories_placeholder')}
                                />
                            </label>

                            <div class="form-actions">
                                <button type="submit" disabled={savingAisle || !aisleName.trim()}>
                                    {savingAisle ? $_('grocery_store.saving_button') : $_('grocery_store.save_aisle_button')}
                                </button>
                                <button type="button" class="secondary" onclick={() => { showNewAisle = false; }}>{$_('common.cancel')}</button>
                            </div>
                        </form>
                    {/if}
                </div>
            </div>
        {/if}
    </div>
</div>

<ConfirmDialog
    open={deleteStoreOpen}
    title={$_('grocery_store.delete_store_confirm')}
    message=""
    confirmLabel={$_('common.delete')}
    variant="danger"
    onconfirm={async () => {
        if (deleteStoreId) await deleteStore(deleteStoreId);
        deleteStoreOpen = false;
        deleteStoreId = null;
    }}
    oncancel={() => { deleteStoreOpen = false; deleteStoreId = null; }}
/>

<style>
    .overlay {
        position: fixed; inset: 0; z-index: 200;
        background: rgba(0,0,0,0.55);
        display: flex; align-items: center; justify-content: center;
        padding: 1rem;
    }
    .standalone {
        display: block;
        padding: 0;
    }
    .standalone .panel {
        max-width: 100%;
        max-height: none;
        border: none;
        border-radius: 0;
        background: transparent;
    }
    .panel {
        background: var(--surface, #1a2232);
        border: 1px solid var(--border, #334);
        border-radius: 10px;
        width: 100%; max-width: 760px;
        max-height: 90vh;
        overflow: hidden;
        display: flex; flex-direction: column;
    }
    .panel-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1rem 1.25rem 0.75rem;
        border-bottom: 1px solid var(--border, #334);
    }
    .panel-header h2 { margin: 0; font-size: 1.1rem; }
    .close-btn {
        background: none; border: none; color: var(--muted, #94a3b8);
        cursor: pointer; font-size: 1.1rem; padding: 0.25rem;
    }
    .close-btn:hover { color: var(--text, #fff); }

    .layout {
        display: flex; flex: 1; overflow: hidden;
    }
    .store-sidebar {
        width: 180px; min-width: 140px;
        border-right: 1px solid var(--border, #334);
        display: flex; flex-direction: column;
        overflow-y: auto;
    }
    .store-list {
        list-style: none; margin: 0; padding: 0.5rem 0; flex: 1;
    }
    .store-list li {
        display: flex; align-items: center; gap: 0; padding: 0 0.5rem;
    }
    .store-list li.active { background: var(--surface-alt, #1e2a3a); }
    .store-name-btn {
        flex: 1; background: none; border: none; text-align: left;
        padding: 0.5rem 0.25rem; cursor: pointer; color: var(--text, #f1f5f9);
        font-size: 0.875rem;
    }
    .del-btn {
        background: none; border: none; color: var(--muted, #64748b);
        cursor: pointer; padding: 0.25rem; font-size: 0.8rem;
        line-height: 1;
    }
    .del-btn:hover { color: var(--danger, #ef4444); }
    .new-store-form {
        display: flex; gap: 0.25rem; padding: 0.5rem;
        border-top: 1px solid var(--border, #334);
    }
    .new-store-form input { flex: 1; min-width: 0; font-size: 0.8rem; padding: 0.3rem 0.4rem; }
    .new-store-form button { padding: 0.3rem 0.5rem; cursor: pointer; font-size: 0.9rem; }
    .cancel-store-btn { background: none; border: none; color: var(--muted, #64748b); cursor: pointer; padding: 0.2rem; line-height: 1; }
    .cancel-store-btn:hover { color: var(--danger, #ef4444); }
    .new-store-card {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.35rem;
        width: 100%;
        padding: 0.5rem;
        border: none;
        border-top: 2px dashed var(--border, #334);
        background: transparent;
        cursor: pointer;
        color: var(--accent, #3b82f6);
        font-size: 0.8rem;
    }
    .new-store-card:hover {
        background: color-mix(in srgb, var(--accent, #3b82f6) 8%, transparent);
        color: var(--accent, #3b82f6);
    }

    .aisle-editor {
        flex: 1; overflow-y: auto; padding: 1rem;
        display: flex; flex-direction: column; gap: 0.75rem;
    }
    .aisle-header, .aisle-form-header {
        display: flex; align-items: center; justify-content: space-between;
    }
    .aisle-title { font-weight: 600; font-size: 0.9rem; }
    .add-aisle-btn, .text-btn {
        background: none; border: 1px solid var(--border, #334);
        border-radius: 4px; padding: 0.25rem 0.6rem;
        font-size: 0.8rem; cursor: pointer; color: var(--text, #f1f5f9);
    }
    .add-aisle-btn:hover, .text-btn:hover { border-color: var(--accent, #3b82f6); color: var(--accent, #3b82f6); }
    .text-btn { border: none; padding: 0; color: var(--accent, #3b82f6); }

    .aisle-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 0.5rem; }
    .aisle-row {
        display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem;
        padding: 0.5rem 0.6rem;
        border: 1px solid var(--border, #334); border-radius: 6px;
        background: var(--surface-alt, #1e2a3a);
    }
    .aisle-info { flex: 1; min-width: 0; }
    .aisle-info strong { font-size: 0.875rem; }
    .slug-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.25rem; }
    .slug-chip {
        font-size: 0.7rem; padding: 0.1rem 0.4rem; border-radius: 99px;
        background: var(--surface, #1a2232); border: 1px solid var(--border, #334);
        color: var(--muted, #94a3b8);
    }
    .aisle-actions { display: flex; gap: 0.25rem; align-items: center; flex-shrink: 0; }
    .aisle-actions button {
        background: none; border: 1px solid var(--border, #334);
        border-radius: 4px; padding: 0.2rem 0.4rem;
        font-size: 0.75rem; cursor: pointer; color: var(--text, #f1f5f9);
    }
    .aisle-actions button:disabled { opacity: 0.35; cursor: default; }
    .aisle-actions button:not(:disabled):hover { border-color: var(--accent, #3b82f6); }

    .aisle-form { display: flex; flex-direction: column; gap: 0.75rem; }
    .aisle-form label > span { display: block; font-size: 0.8rem; margin-bottom: 0.25rem; color: var(--muted, #94a3b8); }
    .aisle-form input[type="text"] { width: 100%; box-sizing: border-box; }
    fieldset { border: 1px solid var(--border, #334); border-radius: 6px; padding: 0.5rem 0.75rem; margin: 0; }
    legend { font-size: 0.8rem; color: var(--muted, #94a3b8); padding: 0 0.25rem; }
    .cat-grid { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.35rem; }
    .cat-chip-label {
        display: inline-flex; align-items: center; gap: 0.3rem;
        padding: 0.25rem 0.6rem; border-radius: 99px; font-size: 0.78rem; cursor: pointer;
        border: 1px solid var(--border, #334); background: var(--surface-alt, #1e2a3a);
        color: var(--muted, #94a3b8); user-select: none; transition: border-color 0.1s, background 0.1s;
    }
    .cat-chip-label input { position: absolute; opacity: 0; width: 0; height: 0; }
    .cat-chip-label.selected {
        border-color: var(--accent, #3b82f6);
        background: color-mix(in srgb, var(--accent, #3b82f6) 18%, transparent);
        color: var(--text, #f1f5f9);
    }
    .form-actions { display: flex; gap: 0.5rem; }

    .empty-hint { color: var(--muted, #94a3b8); font-size: 0.875rem; }
    .error { color: var(--danger, #ef4444); font-size: 0.875rem; }
    .muted { color: var(--muted, #94a3b8); }
    @media (max-width: 640px) {
        .layout { flex-direction: column; }
        .store-sidebar { width: 100%; min-width: 0; border-right: none; border-bottom: 1px solid var(--border, #334); max-height: 160px; }
        .aisle-editor { flex: 1; }
    }
</style>
