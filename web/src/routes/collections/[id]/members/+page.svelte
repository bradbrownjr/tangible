<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { api, type Collection, type Membership, type Role } from '$lib/api';

    let collection = $state<Collection | null>(null);
    let members = $state<Membership[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newIdent = $state('');
    let newRole: Role = $state('viewer');

    const cid = $derived($page.params.id ?? '');

    async function load() {
        loading = true;
        error = '';
        try {
            collection = await api.get<Collection>(`/collections/${cid}`);
            members = await api.get<Membership[]>(`/collections/${cid}/members`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function addMember(e: Event) {
        e.preventDefault();
        if (!newIdent.trim()) return;
        try {
            await api.post(`/collections/${cid}/members`, {
                user_identifier: newIdent.trim(),
                role: newRole
            });
            newIdent = '';
            newRole = 'viewer';
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function changeRole(m: Membership, role: Role) {
        try {
            await api.patch(`/collections/${cid}/members/${m.id}`, { role });
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function removeMember(m: Membership) {
        if (!confirm(`Remove ${m.username} from this collection?`)) return;
        try {
            await api.delete(`/collections/${cid}/members/${m.id}`);
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    onMount(load);
</script>

{#if collection}
    <h1>{collection.name} — Members</h1>
    <p class="muted"><a href="/collections/{cid}">← back to items</a></p>

    {#if error}<p class="error">{error}</p>{/if}

    <form onsubmit={addMember} class="card" style="margin: 1rem 0">
        <div style="display:grid; grid-template-columns: 1fr 140px auto; gap:.5rem">
            <input bind:value={newIdent} placeholder="Username or email" />
            <select bind:value={newRole}>
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
            </select>
            <button type="submit">Add member</button>
        </div>
    </form>

    {#if loading}
        <p class="muted">Loading…</p>
    {:else}
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {#each members as m (m.id)}
                    <tr>
                        <td>{m.display_name ?? m.username}</td>
                        <td class="muted">{m.email ?? ''}</td>
                        <td>
                            {#if m.role === 'owner'}
                                <span class="muted">Owner</span>
                            {:else}
                                <select
                                    value={m.role}
                                    onchange={(e) =>
                                        changeRole(m, (e.currentTarget as HTMLSelectElement).value as Role)}
                                >
                                    <option value="viewer">Viewer</option>
                                    <option value="editor">Editor</option>
                                </select>
                            {/if}
                        </td>
                        <td>
                            {#if m.role !== 'owner'}
                                <button class="danger" onclick={() => removeMember(m)}>Remove</button>
                            {/if}
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
{:else if !loading}
    <p class="error">Collection not found.</p>
{/if}
