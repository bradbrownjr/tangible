<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import {
        api,
        type BundleAssetKind,
        type Collection,
        type Item,
        type ManualBundle
    } from '$lib/api';
    import { Button, ConfirmDialog, Modal } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    const ASSET_KIND_ICON: Record<BundleAssetKind, string> = {
        manual:   'book-open',
        diagram:  'image',
        firmware: 'file-cog',
        service:  'wrench',
        parts:    'nut',
        other:    'file',
    };

    let collection = $state<Collection | null>(null);
    let bundles = $state<ManualBundle[]>([]);
    let items = $state<Item[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newTitle = $state('');
    let newDescription = $state('');

    let editingId = $state<string | null>(null);
    let editTitle = $state('');
    let editDescription = $state('');

    let confirmDeleteId = $state<string | null>(null);
    let confirmDeleteLabel = $state('');
    let confirmDeleting = $state(false);

    let confirmAssetBundleId = $state<string | null>(null);
    let confirmAssetId = $state<string | null>(null);
    let confirmAssetDeleting = $state(false);

    let uploadBundleId = $state<string | null>(null);
    let uploadFile = $state<File | null>(null);
    let uploadLabel = $state('');
    let uploadKind = $state<BundleAssetKind>('manual');
    let uploadBusy = $state(false);

    let linkBundleId = $state<string | null>(null);
    let linkItemId = $state('');

    const cid = $derived(page.params.id ?? '');
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );

    const itemsById = $derived(new Map(items.map((i) => [i.id, i])));

    async function load() {
        loading = true;
        error = '';
        try {
            const [c, b, it] = await Promise.all([
                api.get<Collection>(`/collections/${cid}`),
                api.get<ManualBundle[]>(`/collections/${cid}/bundles`),
                api.get<Item[]>(`/items?collection_id=${cid}&include_archived=false&limit=500`)
            ]);
            collection = c;
            bundles = b;
            items = it;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function createBundle(e: Event) {
        e.preventDefault();
        if (!newTitle.trim()) return;
        try {
            await api.post(`/collections/${cid}/bundles`, {
                title: newTitle.trim(),
                description: newDescription.trim() || null
            });
            newTitle = '';
            newDescription = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function startEdit(b: ManualBundle) {
        editingId = b.id;
        editTitle = b.title;
        editDescription = b.description ?? '';
    }

    async function saveEdit() {
        if (!editingId) return;
        try {
            await api.patch(`/bundles/${editingId}`, {
                title: editTitle.trim(),
                description: editDescription.trim() || null
            });
            editingId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function requestDelete(b: ManualBundle) {
        confirmDeleteId = b.id;
        confirmDeleteLabel = b.title;
    }

    async function deleteConfirmed() {
        if (!confirmDeleteId) return;
        confirmDeleting = true;
        try {
            await api.delete(`/bundles/${confirmDeleteId}`);
            confirmDeleteId = null;
            confirmDeleteLabel = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            confirmDeleting = false;
        }
    }

    function requestAssetDelete(bid: string, aid: string) {
        confirmAssetBundleId = bid;
        confirmAssetId = aid;
    }

    async function deleteAssetConfirmed() {
        if (!confirmAssetBundleId || !confirmAssetId) return;
        confirmAssetDeleting = true;
        try {
            await api.delete(`/bundles/${confirmAssetBundleId}/assets/${confirmAssetId}`);
            confirmAssetBundleId = null;
            confirmAssetId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            confirmAssetDeleting = false;
        }
    }

    function startUpload(bid: string) {
        uploadBundleId = bid;
        uploadFile = null;
        uploadLabel = '';
        uploadKind = 'manual';
    }

    async function doUpload() {
        if (!uploadBundleId || !uploadFile) return;
        uploadBusy = true;
        try {
            const fd = new FormData();
            fd.append('file', uploadFile);
            fd.append('kind', uploadKind);
            if (uploadLabel.trim()) fd.append('label', uploadLabel.trim());
            await api.upload(`/bundles/${uploadBundleId}/assets`, fd);
            uploadBundleId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            uploadBusy = false;
        }
    }

    async function setPrimary(bid: string, aid: string) {
        try {
            await api.patch(`/bundles/${bid}`, { primary_asset_id: aid });
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    async function linkItem() {
        if (!linkBundleId || !linkItemId) return;
        try {
            await api.post(`/bundles/${linkBundleId}/items/${linkItemId}`);
            linkBundleId = null;
            linkItemId = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    async function unlinkItem(bid: string, iid: string) {
        try {
            await api.delete(`/bundles/${bid}/items/${iid}`);
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function fmtBytes(n: number): string {
        if (n < 1024) return `${n} B`;
        if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
        return `${(n / 1024 / 1024).toFixed(1)} MB`;
    }

    onMount(load);
</script>

{#if collection}
    {#if error}<p class="error">{error}</p>{/if}

    <h1>{$_('collections.tab_bundles')}</h1>

    {#if canEdit}
        <form onsubmit={createBundle} class="card" style="margin-bottom: 1.5rem">
            <h2>{$_('bundles.add_heading')}</h2>
            <div class="form-row">
                <input
                    type="text"
                    bind:value={newTitle}
                    placeholder={$_('bundles.title_placeholder')}
                    required
                />
                <input
                    type="text"
                    bind:value={newDescription}
                    placeholder={$_('bundles.description_placeholder')}
                />
                <button type="submit" disabled={!newTitle.trim()}>{$_('bundles.add_button')}</button>
            </div>
        </form>
    {/if}

    {#if loading}
        <p class="muted">Loading…</p>
    {:else if bundles.length === 0}
        <p class="muted">{$_('bundles.no_bundles')}</p>
    {:else}
        {#each bundles as b (b.id)}
            <article class="card bundle">
                {#if editingId === b.id}
                    <div class="form-row">
                        <input bind:value={editTitle} required />
                        <input bind:value={editDescription} placeholder={$_('bundles.description_placeholder')} />
                        <button type="button" onclick={saveEdit}>{$_('bundles.save_button')}</button>
                        <button type="button" class="secondary" onclick={() => (editingId = null)}>{$_('common.cancel')}</button>
                    </div>
                {:else}
                    <header class="bundle-header">
                        <div>
                            <h3>{b.title}</h3>
                            {#if b.description}<p class="muted">{b.description}</p>{/if}
                        </div>
                        {#if canEdit}
                            <div class="bundle-actions">
                                <button type="button" class="secondary" onclick={() => startUpload(b.id)}>{$_('bundles.upload_asset_button')}</button>
                                <button type="button" class="secondary" onclick={() => startEdit(b)}>{$_('bundles.edit_button')}</button>
                                <Button variant="danger" onclick={() => requestDelete(b)}>{$_('bundles.delete_button')}</Button>
                            </div>
                        {/if}
                    </header>

                    <section class="bundle-section">
                        <h4>{$_('bundles.assets_heading')} ({b.assets.length})</h4>
                        {#if b.assets.length === 0}
                            <p class="muted">{$_('bundles.no_assets')}</p>
                        {:else}
                            <ul class="asset-list">
                                {#each b.assets as a (a.id)}
                                    <li>
                                        <Icon name={ASSET_KIND_ICON[a.kind] ?? 'file'} size={14} class="asset-kind-icon" />
                                        <a href="/api/bundles/{b.id}/assets/{a.id}/download" target="_blank" rel="noopener">
                                            {a.label || a.filename}
                                        </a>
                                        <span class="muted">[{a.kind}] {fmtBytes(a.byte_size)}</span>
                                        {#if b.primary_asset_id === a.id}
                                            <span class="badge">{$_('bundles.asset_primary_badge')}</span>
                                        {:else if canEdit}
                                            <button type="button" class="link" onclick={() => setPrimary(b.id, a.id)}>{$_('bundles.make_primary_button')}</button>
                                        {/if}
                                        {#if canEdit}
                                            <button type="button" class="link danger" onclick={() => requestAssetDelete(b.id, a.id)}>{$_('bundles.delete_asset_button')}</button>
                                        {/if}
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                    </section>

                    <section class="bundle-section">
                        <h4>{$_('bundles.linked_items_heading')} ({b.item_ids.length})</h4>
                        {#if b.item_ids.length === 0}
                            <p class="muted">{$_('bundles.no_linked_items')}</p>
                        {:else}
                            <ul class="link-list">
                                {#each b.item_ids as iid (iid)}
                                    <li>
                                        {#if itemsById.get(iid)}
                                            <a href="/items/{iid}">{itemsById.get(iid)?.title}</a>
                                        {:else}
                                            <span class="muted">{iid}</span>
                                        {/if}
                                        {#if canEdit}
                                            <button type="button" class="link danger" onclick={() => unlinkItem(b.id, iid)}>{$_('bundles.unlink_button')}</button>
                                        {/if}
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                        {#if canEdit}
                            <div class="form-row">
                                <select bind:value={linkItemId} onfocus={() => (linkBundleId = b.id)}>
                                    <option value="">{$_('bundles.link_item_placeholder')}</option>
                                    {#each items.filter((i) => !b.item_ids.includes(i.id)) as i (i.id)}
                                        <option value={i.id}>{i.title}</option>
                                    {/each}
                                </select>
                                <button type="button" onclick={() => { linkBundleId = b.id; linkItem(); }} disabled={!linkItemId || linkBundleId !== b.id}>{$_('bundles.link_item_button')}</button>
                            </div>
                        {/if}
                    </section>
                {/if}
            </article>
        {/each}
    {/if}
{/if}

<!-- Upload asset modal -->
<Modal open={!!uploadBundleId} title={$_('bundles.upload_heading')} onclose={() => (uploadBundleId = null)}>
    {#snippet footer()}
        <button type="button" onclick={doUpload} disabled={!uploadFile || uploadBusy}>
            {uploadBusy ? $_('bundles.uploading_button') : $_('bundles.upload_button')}
        </button>
        <button type="button" class="secondary" onclick={() => (uploadBundleId = null)} disabled={uploadBusy}>{$_('common.cancel')}</button>
    {/snippet}
    <div class="form-row">
        <input
            type="file"
            onchange={(e) => (uploadFile = (e.currentTarget as HTMLInputElement).files?.[0] ?? null)}
        />
    </div>
    <div class="form-row">
        <select bind:value={uploadKind}>
            <option value="manual">{$_('bundles.kind_manual')}</option>
            <option value="diagram">{$_('bundles.kind_diagram')}</option>
            <option value="firmware">{$_('bundles.kind_firmware')}</option>
            <option value="service">{$_('bundles.kind_service')}</option>
            <option value="parts">{$_('bundles.kind_parts')}</option>
            <option value="other">{$_('bundles.kind_other')}</option>
        </select>
        <input bind:value={uploadLabel} placeholder={$_('bundles.upload_label_placeholder')} />
    </div>
</Modal>

<!-- Delete asset confirm -->
<ConfirmDialog
    open={!!confirmAssetId}
    confirmLabel={$_('bundles.delete_asset_button')}
    variant="danger"
    loading={confirmAssetDeleting}
    onconfirm={deleteAssetConfirmed}
    oncancel={() => { confirmAssetBundleId = null; confirmAssetId = null; }}
>
    {$_('bundles.delete_asset_confirm')}
</ConfirmDialog>

<!-- Delete bundle confirm -->
<ConfirmDialog
    open={!!confirmDeleteId}
    confirmLabel={$_('bundles.delete_button')}
    variant="danger"
    loading={confirmDeleting}
    onconfirm={deleteConfirmed}
    oncancel={() => { confirmDeleteId = null; confirmDeleteLabel = ''; }}
>
    {$_('bundles.delete_bundle_text', {values: {name: confirmDeleteLabel}})}
</ConfirmDialog>

<style>
    .bundle { margin: 1rem 0; }
    .bundle-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }
    .bundle-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .bundle-section { margin-top: 1rem; }
    .asset-list, .link-list { list-style: none; padding-left: 0; }
    .asset-list li, .link-list li {
        padding: 0.25rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    :global(.asset-kind-icon) { color: var(--text-muted); flex-shrink: 0; }
    .badge { background: var(--accent); color: var(--accent-contrast); padding: 0.1rem 0.5rem; border-radius: var(--radius-full); font-size: 0.75rem; }
    .form-row { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
</style>
