<script lang="ts">
    import { onMount } from 'svelte';
    import { api, type Collection, type Item } from '$lib/api';

    let items = $state<Item[]>([]);
    let collections = $state<Map<string, Collection>>(new Map());
    let loading = $state(true);
    let error = $state('');

    async function load() {
        loading = true;
        try {
            const [fetchedItems, fetchedCollections] = await Promise.all([
                api.get<Item[]>('/items/grocery-list'),
                api.get<Collection[]>('/collections'),
            ]);
            items = fetchedItems;
            collections = new Map(fetchedCollections.map((c) => [c.id, c]));
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function markInStock(item: Item) {
        await api.patch(`/items/${item.id}`, { depleted: false });
        items = items.filter((i) => i.id !== item.id);
    }

    onMount(load);
</script>

<h1>Grocery List</h1>
<p class="muted">Items marked as depleted across all your shared collections.</p>

{#if loading}
    <p class="muted">Loading…</p>
{:else if error}
    <p class="error">{error}</p>
{:else if items.length === 0}
    <p class="muted">Nothing to restock — all clear! 🎉</p>
{:else}
    <table>
        <thead>
            <tr>
                <th>Item</th>
                <th>Collection</th>
                <th>Category</th>
                <th></th>
            </tr>
        </thead>
        <tbody>
            {#each items as item (item.id)}
                <tr>
                    <td>
                        <strong>{item.title}</strong>
                        {#if item.subtitle}<span class="muted"> · {item.subtitle}</span>{/if}
                    </td>
                    <td>
                        <a href="/collections/{item.collection_id}">
                            {collections.get(item.collection_id)?.name ?? item.collection_id}
                        </a>
                    </td>
                    <td class="muted">{item.category_slug ?? ''}</td>
                    <td>
                        <button type="button" onclick={() => markInStock(item)}>
                            Mark in stock
                        </button>
                    </td>
                </tr>
            {/each}
        </tbody>
    </table>
{/if}

<style>
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th, td {
        text-align: left;
        padding: 0.5rem 0.75rem;
        border-bottom: 1px solid var(--border);
    }
    th {
        font-weight: 600;
        color: var(--text-muted, #888);
        font-size: 0.85rem;
    }
</style>
