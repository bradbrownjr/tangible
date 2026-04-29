<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { api, type Collection, type Item } from '$lib/api';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let loading = $state(true);
    let error = $state('');

    const slug = $derived(page.params.slug ?? '');

    async function load() {
        loading = true;
        try {
            collection = await api.get<Collection>(`/public/share/${slug}`);
            items = await api.get<Item[]>(`/public/share/${slug}/items`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    onMount(load);
</script>

{#if loading}
    <p class="muted">Loading…</p>
{:else if error}
    <h1>Not available</h1>
    <p class="error">{error}</p>
    <p class="muted">This share link may be expired or revoked.</p>
{:else if collection}
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}
    <p class="muted">Read-only view shared by the owner.</p>

    {#if items.length === 0}
        <p class="muted">No items to show.</p>
    {:else}
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th>Title</th>
                    <th>Qty</th>
                    <th>Condition</th>
                </tr>
            </thead>
            <tbody>
                {#each items as i (i.id)}
                    <tr>
                        <td class="muted">{i.category_slug ?? ''}</td>
                        <td>
                            {i.title}{#if i.subtitle}
                                <span class="muted">— {i.subtitle}</span>
                            {/if}
                        </td>
                        <td>{i.quantity}</td>
                        <td>{i.condition ?? ''}</td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
{/if}
