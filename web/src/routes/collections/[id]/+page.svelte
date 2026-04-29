<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { api, type Collection, type Item, type ItemType } from '$lib/api';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let search = $state('');
    let typeFilter = $state<ItemType | ''>('');
    let loading = $state(true);
    let error = $state('');

    // Inline create form
    let newType: ItemType = $state('movie');
    let newTitle = $state('');

    const cid = $derived($page.params.id ?? '');

    async function load() {
        loading = true;
        try {
            collection = await api.get<Collection>(`/collections/${cid}`);
            const params = new URLSearchParams({ collection_id: cid });
            if (search) params.set('search', search);
            if (typeFilter) params.set('type', typeFilter);
            items = await api.get<Item[]>(`/items?${params.toString()}`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function addItem(e: Event) {
        e.preventDefault();
        if (!newTitle.trim()) return;
        await api.post('/items', { collection_id: cid, type: newType, title: newTitle.trim() });
        newTitle = '';
        await load();
    }

    async function removeItem(id: string) {
        if (!confirm('Delete this item?')) return;
        await api.delete(`/items/${id}`);
        await load();
    }

    onMount(load);
</script>

{#if collection}
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}
    <p>
        <a href="/collections/{cid}/members">Manage members →</a>
        &nbsp;·&nbsp;
        <a href="/collections/{cid}/templates">Item templates →</a>
    </p>

    <form onsubmit={addItem} class="card" style="margin: 1rem 0">
        <div style="display: grid; grid-template-columns: 140px 1fr auto; gap: .5rem">
            <select bind:value={newType}>
                <option value="movie">Movie</option>
                <option value="music">Music</option>
                <option value="book">Book</option>
                <option value="comic">Comic</option>
                <option value="game">Game</option>
                <option value="other">Other</option>
            </select>
            <input bind:value={newTitle} placeholder="Title" />
            <button type="submit">Add</button>
        </div>
    </form>

    <div style="display:flex; gap:.5rem; margin-bottom: 1rem">
        <input bind:value={search} placeholder="Search title…" oninput={() => load()} />
        <select bind:value={typeFilter} onchange={() => load()}>
            <option value="">All types</option>
            <option value="movie">Movies</option>
            <option value="music">Music</option>
            <option value="book">Books</option>
            <option value="comic">Comics</option>
            <option value="game">Games</option>
            <option value="other">Other</option>
        </select>
    </div>

    {#if loading}
        <p class="muted">Loading…</p>
    {:else if error}
        <p class="error">{error}</p>
    {:else if items.length === 0}
        <p class="muted">No items yet.</p>
    {:else}
        <table>
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Title</th>
                    <th>Qty</th>
                    <th>Condition</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {#each items as i (i.id)}
                    <tr>
                        <td class="muted">{i.type}</td>
                        <td>{i.title}{#if i.subtitle} <span class="muted">— {i.subtitle}</span>{/if}</td>
                        <td>{i.quantity}</td>
                        <td>{i.condition ?? ''}</td>
                        <td>
                            <button class="danger" onclick={() => removeItem(i.id)}>Delete</button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
{:else if !loading}
    <p class="error">Collection not found.</p>
{/if}
