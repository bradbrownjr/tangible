<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import {
        api,
        type BundleAssetKind,
        type Collection,
        type Item,
        type ManualBundle
    } from '$lib/api';

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
        try {
            await api.delete(`/bundles/${confirmDeleteId}`);
            confirmDeleteId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
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

    async function deleteAsset(bid: string, aid: string) {
        if (!confirm('Delete this asset?')) return;
        try {
            await api.delete(`/bundles/${bid}/assets/${aid}`);
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
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}

    <nav class="subnav" aria-label="Collection sections">
        <a class="tab" href="/collections/{cid}">Items</a>
        <a class="tab" href="/collections/{cid}/templates">Templates</a>
        <a class="tab" href="/collections/{cid}/locations">Locations</a>
        <a class="tab tab-active" href="/collections/{cid}/bundles" aria-current="page">Bundles</a>
        <a class="tab" href="/collections/{cid}/chores">Chores</a>
        <a class="tab" href="/collections/{cid}/members">Members</a>
    </nav>

    {#if error}<p class="error">{error}</p>{/if}

    {#if canEdit}
        <form onsubmit={createBundle} class="card" style="margin: 1rem 0">
            <h2>Add manual bundle</h2>
            <div class="form-row">
                <input
                    type="text"
                    bind:value={newTitle}
                    placeholder="Title (e.g. DeWalt DCD777 Manual)"
                    required
                />
                <input
                    type="text"
                    bind:value={newDescription}
                    placeholder="Description (optional)"
                />
                <button type="submit" disabled={!newTitle.trim()}>Add</button>
            </div>
        </form>
    {/if}

    {#if loading}
        <p>Loading…</p>
    {:else if bundles.length === 0}
        <p class="muted">
            No bundles yet. Bundles let you store a manual once and link it to many items
            (e.g. one user manual shared by every unit of an appliance you own).
        </p>
    {:else}
        {#each bundles as b (b.id)}
            <article class="card bundle">
                {#if editingId === b.id}
                    <div class="form-row">
                        <input bind:value={editTitle} required />
                        <input bind:value={editDescription} placeholder="Description" />
                        <button type="button" onclick={saveEdit}>Save</button>
                        <button type="button" class="secondary" onclick={() => (editingId = null)}>Cancel</button>
                    </div>
                {:else}
                    <header class="bundle-header">
                        <div>
                            <h3>{b.title}</h3>
                            {#if b.description}<p class="muted">{b.description}</p>{/if}
                        </div>
                        {#if canEdit}
                            <div class="bundle-actions">
                                <button type="button" class="secondary" onclick={() => startUpload(b.id)}>Upload asset</button>
                                <button type="button" class="secondary" onclick={() => startEdit(b)}>Edit</button>
                                <button type="button" class="danger" onclick={() => requestDelete(b)}>Delete</button>
                            </div>
                        {/if}
                    </header>

                    <section class="bundle-section">
                        <h4>Assets ({b.assets.length})</h4>
                        {#if b.assets.length === 0}
                            <p class="muted">No assets uploaded yet.</p>
                        {:else}
                            <ul class="asset-list">
                                {#each b.assets as a (a.id)}
                                    <li>
                                        <a href="/api/bundles/{b.id}/assets/{a.id}/download" target="_blank" rel="noopener">
                                            {a.label || a.filename}
                                        </a>
                                        <span class="muted">[{a.kind}] {fmtBytes(a.byte_size)}</span>
                                        {#if b.primary_asset_id === a.id}
                                            <span class="badge">primary</span>
                                        {:else if canEdit}
                                            <button type="button" class="link" onclick={() => setPrimary(b.id, a.id)}>Make primary</button>
                                        {/if}
                                        {#if canEdit}
                                            <button type="button" class="link danger" onclick={() => deleteAsset(b.id, a.id)}>Delete</button>
                                        {/if}
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                    </section>

                    <section class="bundle-section">
                        <h4>Linked items ({b.item_ids.length})</h4>
                        {#if b.item_ids.length === 0}
                            <p class="muted">Not linked to any items yet.</p>
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
                                            <button type="button" class="link danger" onclick={() => unlinkItem(b.id, iid)}>Unlink</button>
                                        {/if}
                                    </li>
                                {/each}
                            </ul>
                        {/if}
                        {#if canEdit}
                            <div class="form-row">
                                <select bind:value={linkItemId} onfocus={() => (linkBundleId = b.id)}>
                                    <option value="">— Pick item to link —</option>
                                    {#each items.filter((i) => !b.item_ids.includes(i.id)) as i (i.id)}
                                        <option value={i.id}>{i.title}</option>
                                    {/each}
                                </select>
                                <button type="button" onclick={() => { linkBundleId = b.id; linkItem(); }} disabled={!linkItemId || linkBundleId !== b.id}>Link</button>
                            </div>
                        {/if}
                    </section>
                {/if}
            </article>
        {/each}
    {/if}

    {#if uploadBundleId}
        <div class="modal" role="dialog" aria-modal="true">
            <div class="card">
                <h3>Upload asset</h3>
                <div class="form-row">
                    <input
                        type="file"
                        onchange={(e) => (uploadFile = (e.currentTarget as HTMLInputElement).files?.[0] ?? null)}
                    />
                </div>
                <div class="form-row">
                    <select bind:value={uploadKind}>
                        <option value="manual">Manual</option>
                        <option value="diagram">Diagram</option>
                        <option value="firmware">Firmware</option>
                        <option value="service">Service sheet</option>
                        <option value="parts">Parts list</option>
                        <option value="other">Other</option>
                    </select>
                    <input bind:value={uploadLabel} placeholder="Label (optional)" />
                </div>
                <div class="form-row">
                    <button type="button" onclick={doUpload} disabled={!uploadFile || uploadBusy}>
                        {uploadBusy ? 'Uploading…' : 'Upload'}
                    </button>
                    <button type="button" class="secondary" onclick={() => (uploadBundleId = null)} disabled={uploadBusy}>Cancel</button>
                </div>
            </div>
        </div>
    {/if}

    {#if confirmDeleteId}
        <div class="modal" role="dialog" aria-modal="true">
            <div class="card">
                <p>
                    Delete bundle <strong>{confirmDeleteLabel}</strong>? All assets in this
                    bundle will be removed. Items previously linked will be unlinked but
                    not deleted.
                </p>
                <div class="form-row">
                    <button type="button" class="danger" onclick={deleteConfirmed}>Delete</button>
                    <button type="button" class="secondary" onclick={() => (confirmDeleteId = null)}>Cancel</button>
                </div>
            </div>
        </div>
    {/if}
{/if}

<style>
    .bundle {
        margin: 1rem 0;
    }
    .bundle-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
    }
    .bundle-actions {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .bundle-section {
        margin-top: 1rem;
    }
    .asset-list, .link-list {
        list-style: none;
        padding-left: 0;
    }
    .asset-list li, .link-list li {
        padding: 0.25rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .badge {
        background: var(--color-accent, #4a7);
        color: white;
        padding: 0.1rem 0.5rem;
        border-radius: 4px;
        font-size: 0.75rem;
    }
    .form-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .link {
        background: none;
        border: none;
        color: var(--color-accent, #4a7);
        cursor: pointer;
        padding: 0;
        font-size: inherit;
    }
    .link.danger {
        color: var(--color-danger, #c33);
    }
    .modal {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.4);
        display: grid;
        place-items: center;
        z-index: 50;
    }
</style>
