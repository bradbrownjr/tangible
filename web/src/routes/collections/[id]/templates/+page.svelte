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
    let scaffoldNames = $state<string[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newName = $state('');
    let fields = $state<TemplateField[]>([]);
    let advancedOpen = $state(false);
    let advancedJson = $state('[]');

    // Inline template editing
    let editingTemplateId = $state<string | null>(null);
    let editName = $state('');
    let editFields = $state<TemplateField[]>([]);
    let editAdvancedOpen = $state(false);
    let editAdvancedJson = $state('[]');
    let deleteTemplateId = $state<string | null>(null);
    let deleteTemplateName = $state('');

    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );
    const hasMissingDefaults = $derived.by(() => {
        if (!canEdit || scaffoldNames.length === 0) return false;
        const existing = new Set(templates.map((t) => t.name));
        return scaffoldNames.some((n) => !existing.has(n));
    });

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
            [collection, templates, scaffoldNames] = await Promise.all([
                api.get<Collection>(`/collections/${cid}`),
                api.get<ItemTemplate[]>(`/collections/${cid}/templates`),
                api.get<string[]>(`/collections/${cid}/scaffold-templates`),
            ]);
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

    function requestRemoveTemplate(t: ItemTemplate) {
        deleteTemplateId = t.id;
        deleteTemplateName = t.name;
    }

    async function removeTemplateConfirmed() {
        if (!deleteTemplateId) return;
        try {
            await api.delete(`/templates/${deleteTemplateId}`);
            deleteTemplateId = null;
            deleteTemplateName = '';
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    function startEditTemplate(t: ItemTemplate) {
        editingTemplateId = t.id;
        editName = t.name;
        editFields = t.fields.map((f) => ({ ...f }));
        editAdvancedOpen = false;
        editAdvancedJson = JSON.stringify(editFields, null, 2);
    }

    function cancelEditTemplate() {
        editingTemplateId = null;
    }

    function addEditField() {
        editFields = [...editFields, { key: '', label: '', type: 'text', required: false }];
    }

    function removeEditField(idx: number) {
        editFields = editFields.filter((_, i) => i !== idx);
    }

    function updateEditField(idx: number, patch: Partial<TemplateField>) {
        editFields = editFields.map((f, i) => (i === idx ? { ...f, ...patch } : f));
    }

    function syncEditJsonFromFields() {
        editAdvancedJson = JSON.stringify(editFields, null, 2);
    }

    function syncEditFieldsFromJson() {
        try {
            const parsed = JSON.parse(editAdvancedJson);
            if (Array.isArray(parsed)) editFields = parsed as TemplateField[];
        } catch (e) {
            error = `Invalid JSON: ${(e as Error).message}`;
        }
    }

    async function saveTemplate() {
        if (!editingTemplateId || !editName.trim()) return;
        let payloadFields = editFields;
        if (editAdvancedOpen) {
            try {
                payloadFields = JSON.parse(editAdvancedJson);
                if (!Array.isArray(payloadFields)) throw new Error('must be a JSON array');
            } catch (e) {
                error = `Invalid JSON: ${(e as Error).message}`;
                return;
            }
        }
        payloadFields = payloadFields.filter((f) => f.key && f.key.trim());
        try {
            await api.patch(`/templates/${editingTemplateId}`, {
                name: editName.trim(),
                fields: payloadFields
            });
            editingTemplateId = null;
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function cloneTemplate(t: ItemTemplate) {
        try {
            await api.post(`/templates/${t.id}/clone`, {});
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function createDefaults() {
        try {
            await api.post(`/collections/${cid}/scaffold-templates`, {});
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

    {#if canEdit}
    <form onsubmit={createTemplate} class="card stack">
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
    {/if}

    {#if hasMissingDefaults}
        <div style="margin-bottom:0.75rem">
            <button type="button" class="secondary" onclick={createDefaults}>Create defaults</button>
        </div>
    {/if}

    {#if loading}
        <p class="muted">Loading…</p>
    {:else if templates.length === 0}
        <p class="muted">No templates yet.{canEdit ? ' Create one above.' : ''}</p>
    {:else}
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Fields</th>
                    {#if canEdit}<th></th>{/if}
                </tr>
            </thead>
            <tbody>
                {#each templates as t (t.id)}
                    <tr>
                        <td><strong>{t.name}</strong></td>
                        <td><code>{t.category_slug}</code></td>
                        <td class="muted">
                            {t.fields
                                .map((f) => `${f.key}:${f.type}${f.required ? '*' : ''}`)
                                .join(', ') || '—'}
                        </td>
                        {#if canEdit}
                            <td class="row-actions">
                                <button class="secondary" onclick={() => {
                                    if (editingTemplateId === t.id) cancelEditTemplate();
                                    else startEditTemplate(t);
                                }}>{editingTemplateId === t.id ? 'Cancel' : 'Edit'}</button>
                                <button class="secondary" onclick={() => cloneTemplate(t)}>Clone</button>
                                <button class="danger" onclick={() => requestRemoveTemplate(t)}>Delete</button>
                            </td>
                        {/if}
                    </tr>
                    {#if editingTemplateId === t.id}
                        <tr class="editing-row">
                            <td colspan="{canEdit ? 4 : 3}" style="padding:0.75rem">
                                <div class="stack">
                                    <div class="field">
                                        <label>Template name</label>
                                        <input bind:value={editName} placeholder="e.g. Vinyl LP" />
                                    </div>
                                    <div class="field">
                                        <div class="row-head">
                                            <span>Custom fields</span>
                                            <button type="button" class="link" onclick={() => {
                                                if (!editAdvancedOpen) syncEditJsonFromFields();
                                                editAdvancedOpen = !editAdvancedOpen;
                                            }}>{editAdvancedOpen ? 'Use simple editor' : 'Advanced (JSON)'}</button>
                                        </div>
                                        {#if editAdvancedOpen}
                                            <textarea rows="6" bind:value={editAdvancedJson} onblur={syncEditFieldsFromJson} spellcheck="false" style="font-family:var(--mono,monospace);width:100%"></textarea>
                                        {:else}
                                            {#if editFields.length === 0}
                                                <p class="muted" style="margin:.25rem 0">No custom fields.</p>
                                            {:else}
                                                <table class="fields">
                                                    <thead><tr><th>Key</th><th>Label</th><th>Type</th><th>Req</th><th>Options</th><th></th></tr></thead>
                                                    <tbody>
                                                        {#each editFields as f, idx (idx)}
                                                            <tr>
                                                                <td><input value={f.key} placeholder="key" oninput={(e) => updateEditField(idx, { key: (e.target as HTMLInputElement).value })} /></td>
                                                                <td><input value={f.label} placeholder="Label" oninput={(e) => updateEditField(idx, { label: (e.target as HTMLInputElement).value })} /></td>
                                                                <td><select value={f.type} onchange={(e) => updateEditField(idx, { type: (e.target as HTMLSelectElement).value as TemplateFieldType })}>{#each FIELD_TYPES as ft}<option value={ft}>{ft}</option>{/each}</select></td>
                                                                <td style="text-align:center"><input type="checkbox" checked={f.required ?? false} onchange={(e) => updateEditField(idx, { required: (e.target as HTMLInputElement).checked })} /></td>
                                                                <td>{#if f.type === 'select'}<input value={(f.options ?? []).join(', ')} placeholder="A, B, C" oninput={(e) => updateEditField(idx, { options: (e.target as HTMLInputElement).value.split(',').map((s) => s.trim()).filter(Boolean) })} />{:else}<span class="muted">—</span>{/if}</td>
                                                                <td><button type="button" class="danger" onclick={() => removeEditField(idx)}>×</button></td>
                                                            </tr>
                                                        {/each}
                                                    </tbody>
                                                </table>
                                            {/if}
                                            <button type="button" onclick={addEditField}>+ Add field</button>
                                        {/if}
                                    </div>
                                    <div style="display:flex;gap:0.5rem">
                                        <button onclick={saveTemplate} disabled={!editName.trim()}>Save changes</button>
                                        <button type="button" class="secondary" onclick={cancelEditTemplate}>Cancel</button>
                                    </div>
                                </div>
                            </td>
                        </tr>
                    {/if}
                {/each}
            </tbody>
        </table>
    {/if}
{:else if !loading}
    <p class="error">Collection not found.</p>
{/if}

{#if deleteTemplateId}
    <div class="modal-backdrop" role="presentation" onclick={() => (deleteTemplateId = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-template-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-template-title">Delete template?</h3>
            <p class="muted">Delete template "{deleteTemplateName}"? Items using it keep existing attrs.</p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (deleteTemplateId = null)}>Cancel</button>
                <button type="button" class="danger" onclick={removeTemplateConfirmed}>Delete</button>
            </div>
        </div>
    </div>
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
    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: grid;
        place-items: center;
        padding: 1rem;
        z-index: 40;
    }
    .modal {
        width: min(34rem, 100%);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        display: grid;
        gap: 0.75rem;
    }
    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
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
    .row-actions {
        white-space: nowrap;
        display: flex;
        gap: 0.35rem;
    }
    .editing-row td {
        background: color-mix(in srgb, var(--accent) 6%, var(--surface));
    }
</style>
