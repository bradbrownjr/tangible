<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Collection, type LocationKind, type LocationNode } from '$lib/api';
    import { ConfirmDialog } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    const KIND_ICON: Record<LocationKind, string> = {
        home:      'home',
        floor:     'building',
        room:      'door-open',
        zone:      'map-pin',
        container: 'package',
    };

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
    let confirmDeleting = $state(false);

    const cid = $derived(page.params.id ?? '');
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );

    interface FlatOption { id: string; label: string; depth: number; }
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

    function cancelEdit() { editingId = null; }

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
        confirmDeleting = true;
        try {
            await api.delete(`/locations/${confirmDeleteId}`);
            confirmDeleteId = null;
            confirmDeleteLabel = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            confirmDeleting = false;
        }
    }

    onMount(load);
</script>

{#if collection}
    {#if error}<p class="error">{error}</p>{/if}

    {#if canEdit}
        <form onsubmit={createLocation} class="card" style="margin: 1rem 0">
            <h2>{$_('locations.add_heading')}</h2>
            <div class="form-row">
                <input
                    type="text"
                    bind:value={newName}
                    placeholder={$_('locations.name_placeholder')}
                    required
                />
                <select bind:value={newKind} title={$_('locations.kind_label')}>
                    <option value="home">{$_('locations.kind_home')}</option>
                    <option value="floor">{$_('locations.kind_floor')}</option>
                    <option value="room">{$_('locations.kind_room')}</option>
                    <option value="zone">{$_('locations.kind_zone')}</option>
                    <option value="container">{$_('locations.kind_container')}</option>
                </select>
                <select bind:value={newParentId} title={$_('locations.parent_label')}>
                    <option value="">{$_('locations.parent_toplevel')}</option>
                    {#each flatOptions as opt (opt.id)}
                        <option value={opt.id}>{'\u00a0\u00a0'.repeat(opt.depth)}{opt.label}</option>
                    {/each}
                </select>
                <input type="text" bind:value={newNotes} placeholder={$_('locations.notes_placeholder')} />
                <button type="submit" disabled={!newName.trim()}>{$_('locations.add_button')}</button>
            </div>
        </form>
    {/if}

    {#if loading}
        <p>{$_('common.loading')}</p>
    {:else if tree.length === 0}
        <p class="muted">{$_('locations.no_locations')}</p>
    {:else}
        <ul class="loc-tree" role="tree">
            {#snippet branch(node: LocationNode, depth: number)}
                <li style="padding-left: {depth * 1.25}rem" role="treeitem" aria-selected="false" aria-expanded={node.children.length > 0 || undefined}>
                    {#if editingId === node.id}
                        <div class="form-row">
                            <input bind:value={editName} required />
                            <select bind:value={editKind}>
                                <option value="home">{$_('locations.kind_home')}</option>
                                <option value="floor">{$_('locations.kind_floor')}</option>
                                <option value="room">{$_('locations.kind_room')}</option>
                                <option value="zone">{$_('locations.kind_zone')}</option>
                                <option value="container">{$_('locations.kind_container')}</option>
                            </select>
                            <select bind:value={editParentId}>
                                <option value="">{$_('locations.parent_toplevel')}</option>
                                {#each flatOptions as opt (opt.id)}
                                    {#if opt.id !== node.id}
                                        <option value={opt.id}>{'\u00a0\u00a0'.repeat(opt.depth)}{opt.label}</option>
                                    {/if}
                                {/each}
                            </select>
                            <input bind:value={editNotes} placeholder={$_('locations.notes_placeholder')} />
                            <button type="button" onclick={saveEdit}>{$_('locations.save_button')}</button>
                            <button type="button" class="secondary" onclick={cancelEdit}>{$_('common.cancel')}</button>
                        </div>
                    {:else}
                        <div class="loc-row">
                            <Icon name={KIND_ICON[node.kind] ?? 'map-pin'} size={14} class="loc-kind-icon" />
                            <span class="loc-name">{node.name}</span>
                            <span class="loc-meta muted">{node.kind}</span>
                            {#if node.item_count > 0}
                                <span class="muted">· {node.item_count === 1 ? $_('locations.item_count', {values: {count: node.item_count}}) : $_('locations.items_count', {values: {count: node.item_count}})}</span>
                            {/if}
                            {#if node.notes}
                                <span class="muted">· {node.notes}</span>
                            {/if}
                            {#if canEdit}
                                <span class="loc-actions">
                                    <button type="button" class="secondary" onclick={() => startEdit(node)}>{$_('locations.edit_button')}</button>
                                    <button type="button" class="danger" onclick={() => requestDelete(node)}>{$_('locations.delete_button')}</button>
                                </span>
                            {/if}
                        </div>
                    {/if}
                    {#if node.children.length}
                        <ul role="group">
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
{/if}

<ConfirmDialog
    open={!!confirmDeleteId}
    confirmLabel={$_('locations.delete_button')}
    variant="danger"
    loading={confirmDeleting}
    onconfirm={deleteConfirmed}
    oncancel={() => { confirmDeleteId = null; confirmDeleteLabel = ''; }}
>
    {$_('locations.delete_text', {values: {name: confirmDeleteLabel}})}
</ConfirmDialog>

<style>
    .loc-tree, .loc-tree ul {
        list-style: none;
        padding-left: 0;
    }
    .loc-tree li {
        padding: 0.25rem 0;
    }
    .loc-row {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        flex-wrap: wrap;
        min-height: var(--tap-min);
    }
    :global(.loc-kind-icon) { color: var(--text-muted); flex-shrink: 0; }
    .loc-name { font-weight: 600; }
    .loc-meta { font-size: 0.8rem; }
    .loc-actions {
        margin-left: auto;
        display: inline-flex;
        gap: 0.25rem;
    }
    .form-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
</style>
