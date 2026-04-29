<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import {
        api,
        type Collection,
        type ItemTemplate,
        type TemplateField,
        type TemplateFieldType
    } from '$lib/api';

    const FIELD_TYPES: TemplateFieldType[] = ['text', 'number', 'boolean', 'date', 'url', 'select'];

    let collection = $state<Collection | null>(null);
    let templates = $state<ItemTemplate[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newName = $state('');
    let fields = $state<TemplateField[]>([]);
    let advancedOpen = $state(false);
    let advancedJson = $state('[]');

    const cid = $derived(page.params.id ?? '');
    const targetCategory = $derived(collection?.default_category_slug || 'other.generic');

    function addField() {
        fields = [...fields, { key: '', label: '', type: 'text', required: false }];
    }

    function removeField(idx: number) {
        fields = fields.filter((_, i) => i !== idx);
    }

    function updateField(idx: number, patch: Partial<TemplateField>) {
        fields = fields.map((f, i) => (i === idx ? { ...f, ...patch } : f));
    }

    function syncJsonFromFields() {
        advancedJson = JSON.stringify(
            fields.map((f) => {
                const out: Record<string, unknown> = {
                    key: f.key,
                    label: f.label || f.key,
                    type: f.type
                };
                if (f.required) out.required = true;
                if (f.options && f.options.length) out.options = f.options;
                if (f.default !== undefined && f.default !== '') out.default = f.default;
                return out;
            }),
            null,
            2
        );
    }

    function syncFieldsFromJson() {
        try {
            const parsed = JSON.parse(advancedJson);
            if (Array.isArray(parsed)) {
                fields = parsed as TemplateField[];
                error = '';
            }
        } catch (e) {
            error = `Invalid JSON: ${(e as Error).message}`;
        }
    }

    function toggleAdvanced() {
        if (!advancedOpen) syncJsonFromFields();
        advancedOpen = !advancedOpen;
    }

    async function load() {
        loading = true;
        error = '';
        try {
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
        if (!newName.trim()) return;
        // If the advanced editor is open, prefer its contents.
        let payloadFields = fields;
        if (advancedOpen) {
            try {
                payloadFields = JSON.parse(advancedJson);
                if (!Array.isArray(payloadFields)) throw new Error('must be a JSON array');
            } catch (e) {
                error = `Invalid JSON: ${(e as Error).message}`;
                return;
            }
        }
        // Strip empty rows from the row builder.
        payloadFields = (payloadFields ?? []).filter((f) => f.key && f.key.trim());
        try {
            await api.post(`/collections/${cid}/templates`, {
                name: newName.trim(),
                category_slug: targetCategory,
                fields: payloadFields
            });
            newName = '';
            fields = [];
            advancedJson = '[]';
            advancedOpen = false;
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
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}

    <nav class="subnav" aria-label="Collection sections">
        <a class="tab" href="/collections/{cid}">Items</a>
        <a class="tab tab-active" href="/collections/{cid}/templates" aria-current="page">
            Templates
        </a>
        <a class="tab" href="/collections/{cid}/members">Members</a>
    </nav>

    <p class="muted" style="margin-top:0">
        Templates add custom fields (e.g. <em>Pressing year</em>, <em>Catalog #</em>) to items in
        this collection. New templates land under
        <code>{targetCategory}</code>.
    </p>

    {#if error}<p class="error">{error}</p>{/if}

    <form onsubmit={createTemplate} class="card stack">
        <div class="field">
            <label for="tname">Template name</label>
            <input id="tname" bind:value={newName} placeholder="e.g. Vinyl LP" required />
        </div>

        <div class="field">
            <div class="row-head">
                <span>Custom fields</span>
                <button type="button" class="link" onclick={toggleAdvanced}>
                    {advancedOpen ? 'Use simple editor' : 'Advanced (JSON)'}
                </button>
            </div>

            {#if advancedOpen}
                <textarea
                    rows="8"
                    bind:value={advancedJson}
                    onblur={syncFieldsFromJson}
                    spellcheck="false"
                    style="font-family: var(--mono, monospace); width:100%"
                ></textarea>
                <p class="muted">
                    JSON array of <code>&#123;key,label,type,required?,options?,default?&#125;</code>.
                    Allowed types: {FIELD_TYPES.join(', ')}.
                </p>
            {:else}
                {#if fields.length === 0}
                    <p class="muted" style="margin:.25rem 0 .5rem">No custom fields yet.</p>
                {:else}
                    <table class="fields">
                        <thead>
                            <tr>
                                <th>Key</th>
                                <th>Label</th>
                                <th>Type</th>
                                <th>Required</th>
                                <th>Options (select only)</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each fields as f, idx (idx)}
                                <tr>
                                    <td>
                                        <input
                                            value={f.key}
                                            placeholder="catalog_no"
                                            oninput={(e) =>
                                                updateField(idx, {
                                                    key: (e.target as HTMLInputElement).value
                                                })}
                                        />
                                    </td>
                                    <td>
                                        <input
                                            value={f.label}
                                            placeholder="Catalog #"
                                            oninput={(e) =>
                                                updateField(idx, {
                                                    label: (e.target as HTMLInputElement).value
                                                })}
                                        />
                                    </td>
                                    <td>
                                        <select
                                            value={f.type}
                                            onchange={(e) =>
                                                updateField(idx, {
                                                    type: (e.target as HTMLSelectElement)
                                                        .value as TemplateFieldType
                                                })}
                                        >
                                            {#each FIELD_TYPES as t}
                                                <option value={t}>{t}</option>
                                            {/each}
                                        </select>
                                    </td>
                                    <td style="text-align:center">
                                        <input
                                            type="checkbox"
                                            checked={f.required ?? false}
                                            onchange={(e) =>
                                                updateField(idx, {
                                                    required: (e.target as HTMLInputElement)
                                                        .checked
                                                })}
                                        />
                                    </td>
                                    <td>
                                        {#if f.type === 'select'}
                                            <input
                                                value={(f.options ?? []).join(', ')}
                                                placeholder="A, B, C"
                                                oninput={(e) =>
                                                    updateField(idx, {
                                                        options: (e.target as HTMLInputElement)
                                                            .value
                                                            .split(',')
                                                            .map((s) => s.trim())
                                                            .filter(Boolean)
                                                    })}
                                            />
                                        {:else}
                                            <span class="muted">—</span>
                                        {/if}
                                    </td>
                                    <td>
                                        <button
                                            type="button"
                                            class="danger"
                                            onclick={() => removeField(idx)}
                                        >
                                            ×
                                        </button>
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                {/if}
                <button type="button" onclick={addField}>+ Add field</button>
            {/if}
        </div>

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
                            {t.fields
                                .map((f) => `${f.key}:${f.type}${f.required ? '*' : ''}`)
                                .join(', ')}
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

<style>
    .subnav {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
        margin: 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid var(--border);
    }
    .tab {
        display: inline-flex;
        align-items: center;
        padding: 0.4rem 0.8rem;
        font: inherit;
        font-weight: 500;
        color: var(--fg);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        text-decoration: none;
        cursor: pointer;
    }
    .tab:hover {
        border-color: var(--accent);
    }
    .tab-active {
        background: var(--accent);
        color: var(--accent-fg, white);
        border-color: var(--accent);
    }
    .stack {
        display: grid;
        gap: 0.75rem;
    }
    .row-head {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 0.25rem;
    }
    .link {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        color: var(--accent);
        cursor: pointer;
        text-decoration: underline;
    }
    .fields th,
    .fields td {
        padding: 0.25rem 0.4rem;
        vertical-align: middle;
    }
    .fields input,
    .fields select {
        width: 100%;
    }
</style>
