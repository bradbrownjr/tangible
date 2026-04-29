<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { api, type Category, type Collection, type Item } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let categories = $state<Category[]>([]);
    let search = $state('');
    // Filter is by top-level root slug (matches subtree); empty = all.
    let rootFilter = $state('');
    let loading = $state(true);
    let error = $state('');

    // Inline create form: cascading root → leaf.
    let newRoot = $state('movies');
    let newLeaf = $state('movies.dvd');
    let newTitle = $state('');
    let scrapeUrl = $state('');
    let scraping = $state(false);

    const cid = $derived(page.params.id ?? '');
    const roots = $derived(rootCategories(categories));
    const leaves = $derived.by(() => {
        const root = categories.find((c) => c.slug === newRoot);
        if (!root) return [];
        return childrenOf(categories, root.id);
    });

    $effect(() => {
        if (leaves.length && !leaves.some((l) => l.slug === newLeaf)) {
            newLeaf = leaves[0].slug;
        }
    });

    async function load() {
        loading = true;
        try {
            if (categories.length === 0) categories = await loadCategories();
            collection = await api.get<Collection>(`/collections/${cid}`);
            const params = new URLSearchParams({ collection_id: cid });
            if (search) params.set('search', search);
            if (rootFilter) params.set('category_subtree', rootFilter);
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
        await api.post('/items', {
            collection_id: cid,
            category: newLeaf,
            title: newTitle.trim()
        });
        newTitle = '';
        await load();
    }

    async function scrapeFromUrl() {
        const url = scrapeUrl.trim();
        if (!url) return;
        scraping = true;
        error = '';
        try {
            const res = await api.post<{ title?: string; category?: string }>(
                '/metadata/scrape',
                { url }
            );
            if (res.title) newTitle = res.title;
            if (res.category) {
                const leaf = categories.find((c) => c.slug === res.category);
                if (leaf?.parent_id) {
                    const root = categories.find((c) => c.id === leaf.parent_id);
                    if (root) newRoot = root.slug;
                    newLeaf = leaf.slug;
                }
            }
            scrapeUrl = '';
        } catch (e) {
            error = (e as Error).message;
        } finally {
            scraping = false;
        }
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
        <div style="display:grid; grid-template-columns:1fr auto; gap:.5rem; margin-bottom:.5rem">
            <input
                bind:value={scrapeUrl}
                placeholder="Paste URL to prefill (Open Library, any web page)…"
            />
            <button type="button" onclick={scrapeFromUrl} disabled={scraping}>
                {scraping ? 'Scraping…' : 'Scrape URL'}
            </button>
        </div>
        <div style="display: grid; grid-template-columns: 140px 160px 1fr auto; gap: .5rem">
            <select bind:value={newRoot}>
                {#each roots as r (r.id)}
                    <option value={r.slug}>{r.name}</option>
                {/each}
            </select>
            <select bind:value={newLeaf}>
                {#each leaves as l (l.id)}
                    <option value={l.slug}>{l.name}</option>
                {/each}
            </select>
            <input bind:value={newTitle} placeholder="Title" />
            <button type="submit">Add</button>
        </div>
    </form>

    <div style="display:flex; gap:.5rem; margin-bottom: 1rem">
        <input bind:value={search} placeholder="Search title…" oninput={() => load()} />
        <select bind:value={rootFilter} onchange={() => load()}>
            <option value="">All categories</option>
            {#each roots as r (r.id)}
                <option value={r.slug}>{r.name}</option>
            {/each}
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
                    <th>Category</th>
                    <th>Title</th>
                    <th>Qty</th>
                    <th>Condition</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {#each items as i (i.id)}
                    <tr>
                        <td class="muted">{i.category_slug ?? ''}</td>
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
