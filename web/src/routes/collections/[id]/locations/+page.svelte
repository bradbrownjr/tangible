<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { api, type Collection, type LocationKind, type LocationNode } from '$lib/api';

    let collection = $state<Collection | null>(null);
    let tree = $state<LocationNode[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newName = $state('');
    let newKind = $state<LocationKind>('room');
    let newParentId = $state('');
    let newNotes = $state('');

    let editingId = $state<string | null>(null);
    let editName = $state('');
    let editKind = $state<LocationKind>('room');
    let editParentId = $state('');
    let editNotes = $state('');

    let confirmDeleteId = $state<string | null>(null);
    let confirmDeleteLabel = $state('');

    const cid = $derived(page.params.id ?? '');
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );

    interface FlatOption {
        id: string;
        label: string;
        depth: number;
    }
    const flatOptions = $derived.by(() => {
        const out: FlatOption[] = [];
        const walk = (nodes: LocationNode[], depth: number) => {
            for (const n of nodes) {
                out.push({ id: n.id, label: n.name, depth });
                walk(n.children, depth + 1);
            }
        };
        walk(tree, 0);
        return out;
    });

    async function load() {
        loading = true;
        error = '';
        try {
            collection = await api.get<Collection>(`/collections/${cid}`);
            tree = await api.get<LocationNode[]>(`/locations?collection_id=${cid}`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function createLocation(e: Event) {
        e.preventDefault();
        if (!newName.trim()) return;
        try {
            await api.post('/locations', {
                collection_id: cid,
                name: newName.trim(),
                kind: newKind,
                parent_id: newParentId || null,
                notes: newNotes.trim() || null,
            });
            newName = '';
            newNotes = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function startEdit(node: LocationNode) {
        editingId = node.id;
        editName = node.name;
        editKind = node.kind;
        editParentId = node.parent_id ?? '';
        editNotes = node.notes ?? '';
    }

    function cancelEdit() {
        editingId = null;
    }

    async function saveEdit() {
        if (!editingId) return;
        try {
            await api.patch(`/locations/${editingId}`, {
                name: editName.trim(),
                kind: editKind,
                parent_id: editParentId || null,
                notes: editNotes.trim() || null,
            });
            editingId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function requestDelete(node: LocationNode) {
        confirmDeleteId = node.id;
        confirmDeleteLabel = node.name;
    }

    async function deleteConfirmed() {
        if (!confirmDeleteId) return;
        try {
            await api.delete(`/locations/${confirmDeleteId}`);
            confirmDeleteId = null;
            confirmDeleteLabel = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    onMount(load);
</script>

{#if collection}
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}

    <nav class="subnav" aria-label="Collection sections">
        <a class="tab" href="/collections/{cid}">Items</a>
        <a class="tab" href="/collections/{cid}/templates">Templates</a>
        <a class="tab tab-active" href="/collections/{cid}/locations" aria-current="page">Locations</a>
        <a class="tab" href="/collections/{cid}/bundles">Bundles</a>
        <a class="tab" href="/collections/{cid}/chores">Chores</a>
        <a class="tab" href="/collections/{cid}/members">Members</a>
    </nav>

    {#if error}<p class="error">{error}</p>{/if}

    {#if canEdit}
        <form onsubmit={createLocation} class="card" style="margin: 1rem 0">
            <h2>Add location</h2>
            <div class="form-row">
                <input
                    type="text"
                    bind:value={newName}
                    placeholder="Name (e.g. Garage, Top shelf)"
                    required
                />
                <select bind:value={newKind} title="Location kind">
                    <option value="home">Home</option>
                    <option value="floor">Floor</option>
                    <option value="room">Room</option>
                    <option value="zone">Zone</option>
                    <option value="container">Container</option>
                </select>
                <select bind:value={newParentId} title="Parent location">
                    <option value="">— Top-level —</option>
                    {#each flatOptions as opt (opt.id)}
                        <option value={opt.id}>{'\u00a0\u00a0'.repeat(opt.depth)}{opt.label}</option>
                    {/each}
                </select>
                <input type="text" bind:value={newNotes} placeholder="Notes (optional)" />
                <button type="submit" disabled={!newName.trim()}>Add</button>
            </div>
        </form>
    {/if}

    {#if loading}
        <p>Loading…</p>
    {:else if tree.length === 0}
        <p class="muted">No locations yet. Create one above to start organizing items.</p>
    {:else}
        <ul class="loc-tree">
            {#snippet branch(node: LocationNode, depth: number)}
                <li style="padding-left: {depth * 1.5}rem">
                    {#if editingId === node.id}
                        <div class="form-row">
                            <input bind:value={editName} required />
                            <select bind:value={editKind}>
                                <option value="home">Home</option>
                                <option value="floor">Floor</option>
                                <option value="room">Room</option>
                                <option value="zone">Zone</option>
                                <option value="container">Container</option>
                            </select>
                            <select bind:value={editParentId}>
                                <option value="">— Top-level —</option>
                                {#each flatOptions as opt (opt.id)}
                                    {#if opt.id !== node.id}
                                        <option value={opt.id}>{'\u00a0\u00a0'.repeat(opt.depth)}{opt.label}</option>
                                    {/if}
                                {/each}
                            </select>
                            <input bind:value={editNotes} placeholder="Notes" />
                            <button type="button" onclick={saveEdit}>Save</button>
                            <button type="button" class="secondary" onclick={cancelEdit}>Cancel</button>
                        </div>
                    {:else}
                        <span class="loc-name"><strong>{node.name}</strong></span>
                        <span class="muted">[{node.kind}]</span>
                        {#if node.item_count > 0}
                            <span class="muted">· {node.item_count} {node.item_count === 1 ? 'item' : 'items'}</span>
                        {/if}
                        {#if node.notes}
                            <span class="muted">· {node.notes}</span>
                        {/if}
                        {#if canEdit}
                            <span class="loc-actions">
                                <button type="button" class="secondary" onclick={() => startEdit(node)}>Edit</button>
                                <button type="button" class="danger" onclick={() => requestDelete(node)}>Delete</button>
                            </span>
                        {/if}
                    {/if}
                    {#if node.children.length}
                        <ul>
                            {#each node.children as child (child.id)}
                                {@render branch(child, depth + 1)}
                            {/each}
                        </ul>
                    {/if}
                </li>
            {/snippet}
            {#each tree as root (root.id)}
                {@render branch(root, 0)}
            {/each}
        </ul>
    {/if}

    {#if confirmDeleteId}
        <div class="modal" role="dialog" aria-modal="true">
            <div class="card">
                <p>
                    Delete <strong>{confirmDeleteLabel}</strong> and all its child locations?
                    Items currently assigned to any of these locations will be unassigned.
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
    .loc-tree {
        list-style: none;
        padding-left: 0;
    }
    .loc-tree ul {
        list-style: none;
        padding-left: 0;
    }
    .loc-tree li {
        padding: 0.35rem 0;
    }
    .loc-name {
        margin-right: 0.5rem;
    }
    .loc-actions {
        margin-left: 0.75rem;
        display: inline-flex;
        gap: 0.25rem;
    }
    .form-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
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
