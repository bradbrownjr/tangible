<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { api, type Category, type Collection, type ItemTemplate, type TemplateField, type TemplateFieldType } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';

    const FIELD_TYPES: TemplateFieldType[] = ['text', 'number', 'boolean', 'date', 'url', 'select'];

    let collection = $state<Collection | null>(null);
    let templates = $state<ItemTemplate[]>([]);
    let categories = $state<Category[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newName = $state('');
    let newRoot = $state('other');
    let newLeaf = $state('other.generic');
    let newFieldsJson = $state('[]');
    const placeholderExample = '[{"key":"isbn","label":"ISBN","type":"text","required":true}]';

    const cid = $derived(page.params.id ?? '');
    const roots = $derived(rootCategories(categories));
    const leaves = $derived.by(() => {
        const root = categories.find((c) => c.slug === newRoot);
        if (!root) return [];
        return childrenOf(categories, root.id);
    });

    $effect(() => {
        // Reset leaf when root changes if current leaf is no longer valid.
        if (leaves.length && !leaves.some((l) => l.slug === newLeaf)) {
            newLeaf = leaves[0].slug;
        }
    });

    async function load() {
        loading = true;
        error = '';
        try {
            categories = await loadCategories();
            collection = await api.get<Collection>(`/collections/${cid}`);
            templates = await api.get<ItemTemplate[]>(`/collections/${cid}/templates`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function createTemplate(e: Event) {
        e.preventDefault();
        try {
            const fields: TemplateField[] = JSON.parse(newFieldsJson);
            await api.post(`/collections/${cid}/templates`, {
                name: newName.trim(),
                category_slug: newLeaf,
                fields
            });
            newName = '';
            newFieldsJson = '[]';
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function removeTemplate(t: ItemTemplate) {
        if (!confirm(`Delete template "${t.name}"? Items using it keep their attrs.`)) return;
        try {
            await api.delete(`/templates/${t.id}`);
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    onMount(load);
</script>

{#if collection}
    <h1>{collection.name} — Templates</h1>
    <p class="muted"><a href="/collections/{cid}">← back to items</a></p>

    {#if error}<p class="error">{error}</p>{/if}

    <form onsubmit={createTemplate} class="card" style="margin: 1rem 0; display:grid; gap:.5rem">
        <div style="display:grid; grid-template-columns: 1fr 160px 200px; gap:.5rem">
            <input bind:value={newName} placeholder="Template name" required />
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
        </div>
        <label>
            Fields (JSON array of <code>&#123;key,label,type,required?,default?,options?&#125;</code>)
            <textarea
                rows="6"
                bind:value={newFieldsJson}
                placeholder={placeholderExample}
            ></textarea>
        </label>
        <p class="muted">Allowed field types: {FIELD_TYPES.join(', ')}</p>
        <div><button type="submit">Create template</button></div>
    </form>

    {#if loading}
        <p class="muted">Loading…</p>
    {:else if templates.length === 0}
        <p class="muted">No templates yet.</p>
    {:else}
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Fields</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {#each templates as t (t.id)}
                    <tr>
                        <td>{t.name}</td>
                        <td><code>{t.category_slug}</code></td>
                        <td class="muted">
                            {t.fields.map((f) => `${f.key}:${f.type}${f.required ? '*' : ''}`).join(', ')}
                        </td>
                        <td>
                            <button class="danger" onclick={() => removeTemplate(t)}>Delete</button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
{:else if !loading}
    <p class="error">Collection not found.</p>
{/if}
