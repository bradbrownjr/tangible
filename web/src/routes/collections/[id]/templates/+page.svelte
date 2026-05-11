<script lang="ts">
    import { onMount } from 'svelte';
    import { _ } from 'svelte-i18n';
    import { page } from '$app/state';
    import {
        api,
        type Category,
        type Collection,
        type ItemTemplate,
        type ScaffoldTemplate,
        type ScraperRegistryEntry,
        type TemplateField,
        type TemplateFieldType
    } from '$lib/api';
    import { loadCategories } from '$lib/categories';
    import { Button, ConfirmDialog, Modal } from '$lib/components';

    const FIELD_TYPES: TemplateFieldType[] = [
        'text', 'number', 'boolean', 'date', 'url', 'select', 'multi_value', 'relation'
    ];

    let collection = $state<Collection | null>(null);
    let templates = $state<ItemTemplate[]>([]);
    let scaffoldNames = $state<string[]>([]);
    let scaffoldPreview = $state<ScaffoldTemplate[]>([]);
    let scaffoldPreviewOpen = $state(false);
    let registryEntries = $state<ScraperRegistryEntry[]>([]);
    let categories = $state<Category[]>([]);
    let loading = $state(true);
    let error = $state('');

    let wizardOpen = $state(false);
    let wizardStep = $state<1 | 2>(1);
    let newCategory = $state('');
    let newName = $state('');
    let fields = $state<TemplateField[]>([]);
    let advancedOpen = $state(false);
    let advancedJson = $state('[]');

    let scraperOpen = $state(false);
    let importingRegistryId = $state<string | null>(null);

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
    const scaffoldRoot = $derived((collection?.default_category_slug || '').split('.')[0]);
    const scaffoldRootLabel = $derived(
        scaffoldRoot
            ? scaffoldRoot.split('_').map((p: string) => p[0]?.toUpperCase() + p.slice(1)).join(' ')
            : 'default'
    );
    const registryById = $derived(new Map(registryEntries.map((e) => [e.id, e])));

    function categoryLabel(slug: string | null | undefined): string {
        if (!slug) return '';
        const leaf = categories.find((c) => c.slug === slug);
        if (!leaf) return slug;
        if (!leaf.parent_id) return leaf.name;
        const parent = categories.find((c) => c.id === leaf.parent_id);
        return parent ? `${parent.name} \u203a ${leaf.name}` : leaf.name;
    }

    function addField() { fields = [...fields, { key: '', label: '', type: 'text', required: false }]; }
    function removeField(idx: number) { fields = fields.filter((_, i) => i !== idx); }
    function updateField(idx: number, patch: Partial<TemplateField>) {
        fields = fields.map((f, i) => (i === idx ? { ...f, ...patch } : f));
    }
    function syncJsonFromFields() {
        advancedJson = JSON.stringify(
            fields.map((f) => {
                const out: Record<string, unknown> = { key: f.key, label: f.label || f.key, type: f.type };
                if (f.required) out.required = true;
                if (f.type === 'select') out.select_source = f.select_source ?? 'static';
                if (f.type === 'relation') out.relation_scope = f.relation_scope ?? 'same_collection';
                if (f.options?.length) out.options = f.options;
                if (f.default !== undefined && f.default !== '') out.default = f.default;
                return out;
            }),
            null, 2
        );
    }
    function syncFieldsFromJson() {
        try {
            const parsed = JSON.parse(advancedJson);
            if (Array.isArray(parsed)) { fields = parsed as TemplateField[]; error = ''; }
        } catch (e) { error = `Invalid JSON: ${(e as Error).message}`; }
    }

    function addEditField() { editFields = [...editFields, { key: '', label: '', type: 'text', required: false }]; }
    function removeEditField(idx: number) { editFields = editFields.filter((_, i) => i !== idx); }
    function updateEditField(idx: number, patch: Partial<TemplateField>) {
        editFields = editFields.map((f, i) => (i === idx ? { ...f, ...patch } : f));
    }
    function syncEditJsonFromFields() { editAdvancedJson = JSON.stringify(editFields, null, 2); }
    function syncEditFieldsFromJson() {
        try {
            const parsed = JSON.parse(editAdvancedJson);
            if (Array.isArray(parsed)) editFields = parsed as TemplateField[];
        } catch (e) { error = `Invalid JSON: ${(e as Error).message}`; }
    }

    async function load() {
        loading = true;
        error = '';
        try {
            [collection, templates, scaffoldNames, scaffoldPreview, registryEntries, categories] = await Promise.all([
                api.get<Collection>(`/collections/${cid}`),
                api.get<ItemTemplate[]>(`/collections/${cid}/templates`),
                api.get<string[]>(`/collections/${cid}/scaffold-templates`),
                api.get<ScaffoldTemplate[]>(`/collections/${cid}/scaffold-templates/preview`),
                api.get<ScraperRegistryEntry[]>(`/metadata/registry`),
                loadCategories(),
            ]);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    function openWizard() {
        wizardStep = 1;
        newCategory = targetCategory;
        newName = '';
        fields = [];
        advancedOpen = false;
        advancedJson = '[]';
        wizardOpen = true;
    }

    function closeWizard() {
        wizardOpen = false;
        scraperOpen = false;
    }

    async function createTemplate() {
        if (!newName.trim()) return;
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
        payloadFields = (payloadFields ?? []).filter((f) => f.key?.trim());
        try {
            await api.post(`/collections/${cid}/templates`, {
                name: newName.trim(),
                category_slug: newCategory || targetCategory,
                fields: payloadFields
            });
            closeWizard();
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function importRegistryEntry(entry: ScraperRegistryEntry) {
        importingRegistryId = entry.id;
        try {
            await api.post('/metadata/registry/import', {
                collection_id: cid,
                entry_ids: [entry.id]
            });
            scraperOpen = false;
            closeWizard();
            await load();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            importingRegistryId = null;
        }
    }

    function startEditTemplate(t: ItemTemplate) {
        editingTemplateId = t.id;
        editName = t.name;
        editFields = t.fields.map((f) => ({ ...f }));
        editAdvancedOpen = false;
        editAdvancedJson = JSON.stringify(editFields, null, 2);
    }

    function cancelEditTemplate() { editingTemplateId = null; }

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
        payloadFields = payloadFields.filter((f) => f.key?.trim());
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

    onMount(load);
</script>

{#if collection}
    <h1>{$_('collections.tab_templates')}</h1>
    <p class="muted intro">
        Templates add custom fields (e.g. <em>Pressing year</em>, <em>Catalog&#x202F;#</em>) to items
        in this collection. Each template extends the built-in fields for its category. Items inherit
        the matching template automatically based on their category.
    </p>

    {#if error}<p class="error">{error}</p>{/if}

    <div class="toolbar">
        {#if canEdit}
            <button onclick={openWizard}>+ New template</button>
        {/if}
        {#if scaffoldPreview.length > 0}
            <button
                type="button"
                class="secondary"
                onclick={() => (scaffoldPreviewOpen = !scaffoldPreviewOpen)}
                aria-expanded={scaffoldPreviewOpen}
            >{scaffoldPreviewOpen ? 'Hide scaffold preview' : 'View scaffold templates'}</button>
        {/if}
        {#if hasMissingDefaults}
            <button type="button" class="secondary" onclick={createDefaults}>
                Create {scaffoldRootLabel} defaults
            </button>
        {/if}
    </div>

    {#if scaffoldPreviewOpen && scaffoldPreview.length > 0}
        <div class="scaffold-preview">
            <p class="muted hint">These templates are seeded when you click <strong>Create {scaffoldRootLabel} defaults</strong>. Templates whose names already exist are skipped.</p>
            {#each scaffoldPreview as s (s.name)}
                <details class="scaffold-entry">
                    <summary>
                        <strong>{s.name}</strong>
                        <code class="slug">{s.category_slug}</code>
                        <span class="muted">{s.fields.length} field{s.fields.length !== 1 ? 's' : ''}</span>
                    </summary>
                    <table class="fields-preview">
                        <thead><tr><th>Key</th><th>Label</th><th>Type</th><th>Options / notes</th></tr></thead>
                        <tbody>
                            {#each s.fields as f (f.key)}
                                <tr>
                                    <td><code>{f.key}</code>{#if f.required}<span class="req" title="required"> *</span>{/if}</td>
                                    <td>{f.label}</td>
                                    <td><code>{f.type}</code></td>
                                    <td class="muted">{#if f.options?.length}{f.options.join(', ')}{:else if f.default !== undefined && f.default !== null}default: {f.default}{:else}—{/if}</td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </details>
            {/each}
        </div>
    {/if}

    {#if loading}
        <p class="muted">Loading&#x2026;</p>
    {:else if templates.length === 0}
        <p class="muted">No templates yet.{canEdit ? ' Use \u201c+ New template\u201d to create one.' : ''}</p>
    {:else}
        <div class="table-wrap">
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
                            <td>
                                <div class="name-cell">
                                    <strong>{t.name}</strong>
                                    {#if t.scraper_id}
                                        {@const entry = registryById.get(t.scraper_id)}
                                        {#if entry}
                                            <span class="linked-pill" title="Imported from community registry">
                                                Linked to: {entry.name}
                                            </span>
                                        {/if}
                                    {/if}
                                </div>
                            </td>
                            <td><code title={t.category_slug}>{categoryLabel(t.category_slug)}</code></td>
                            <td class="muted">
                                {t.fields
                                    .map((f) => `${f.key}:${f.type}${f.required ? '*' : ''}`)
                                    .join(', ') || '&#x2014;'}
                            </td>
                            {#if canEdit}
                                <td class="row-actions">
                                    <button
                                        class="secondary"
                                        onclick={() => {
                                            if (editingTemplateId === t.id) cancelEditTemplate();
                                            else startEditTemplate(t);
                                        }}
                                    >{editingTemplateId === t.id ? 'Cancel' : 'Edit'}</button>
                                    <button class="secondary" onclick={() => cloneTemplate(t)}>Clone</button>
                                    <Button variant="danger" onclick={() => requestRemoveTemplate(t)}>Delete</Button>
                                </td>
                            {/if}
                        </tr>
                        {#if editingTemplateId === t.id}
                            <tr class="editing-row">
                                <td colspan="{canEdit ? 4 : 3}" style="padding:0.75rem">
                                    <div class="stack">
                                        <div class="field">
                                            <label for="edit-template-name">Template name</label>
                                            <input id="edit-template-name" bind:value={editName} placeholder="e.g. Vinyl LP" />
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
                                                        <thead><tr><th>Key</th><th>Label</th><th>Type</th><th>Req</th><th>Source</th><th>Options</th><th></th></tr></thead>
                                                        <tbody>
                                                            {#each editFields as f, idx (idx)}
                                                                <tr>
                                                                    <td><input value={f.key} placeholder="key" oninput={(e) => updateEditField(idx, { key: (e.target as HTMLInputElement).value })} /></td>
                                                                    <td><input value={f.label} placeholder="Label" oninput={(e) => updateEditField(idx, { label: (e.target as HTMLInputElement).value })} /></td>
                                                                    <td><select value={f.type} onchange={(e) => updateEditField(idx, { type: (e.target as HTMLSelectElement).value as TemplateFieldType })}>{#each FIELD_TYPES as ft}<option value={ft}>{ft}</option>{/each}</select></td>
                                                                    <td style="text-align:center"><input type="checkbox" checked={f.required ?? false} onchange={(e) => updateEditField(idx, { required: (e.target as HTMLInputElement).checked })} /></td>
                                                                    <td>{#if f.type === 'select'}<select value={f.select_source ?? 'static'} onchange={(e) => updateEditField(idx, { select_source: (e.target as HTMLSelectElement).value as 'static' | 'dynamic' })}><option value="static">Static list</option><option value="dynamic">Dynamic from used values</option></select>{:else if f.type === 'relation'}<select value={f.relation_scope ?? 'same_collection'} onchange={(e) => updateEditField(idx, { relation_scope: (e.target as HTMLSelectElement).value as 'same_collection' | 'any_collection' })}><option value="same_collection">Same collection</option><option value="any_collection">Any collection</option></select>{:else}<span class="muted">&#x2014;</span>{/if}</td>
                                                                    <td>{#if f.type === 'select' && (f.select_source ?? 'static') === 'static'}<input value={(f.options ?? []).join(', ')} placeholder="A, B, C" oninput={(e) => updateEditField(idx, { options: (e.target as HTMLInputElement).value.split(',').map((s) => s.trim()).filter(Boolean) })} />{:else if f.type === 'select'}<span class="muted">Auto from existing item values</span>{:else if f.type === 'relation'}<span class="muted">Resolved by item id</span>{:else}<span class="muted">&#x2014;</span>{/if}</td>
                                                                    <td><Button variant="danger" size="sm" onclick={() => removeEditField(idx)}>×</Button></td>
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
        </div>
    {/if}
{:else if !loading}
    <p class="error">Collection not found.</p>
{/if}

<ConfirmDialog
    open={!!deleteTemplateId}
    confirmLabel="Delete"
    variant="danger"
    onconfirm={removeTemplateConfirmed}
    oncancel={() => { deleteTemplateId = null; deleteTemplateName = ''; }}
>
    Delete template "{deleteTemplateName}"? Items using it keep their existing attributes.
</ConfirmDialog>

<Modal
    bind:open={wizardOpen}
    title={wizardStep === 1 ? 'New template \u2014 pick a category' : 'New template \u2014 add fields'}
    width="50rem"
    onclose={closeWizard}
>
    {#snippet footer()}
        {#if wizardStep === 1}
            <button
                type="button"
                onclick={() => (wizardStep = 2)}
                disabled={!newName.trim()}
            >Next: Add fields</button>
        {:else}
            <button
                type="button"
                onclick={createTemplate}
                disabled={!newName.trim()}
            >Create template</button>
            <button type="button" class="secondary" onclick={() => (wizardStep = 1)}>&larr; Back</button>
        {/if}
        <button type="button" class="secondary" onclick={closeWizard}>Cancel</button>
    {/snippet}

    {#if wizardStep === 1}
        <div class="stack">
            <div class="field">
                <label for="new-template-name">Template name <span class="req">*</span></label>
                <input
                    id="new-template-name"
                    bind:value={newName}
                    placeholder="e.g. Vinyl LP"
                />
            </div>
            <div class="field">
                <label for="new-template-category">Category</label>
                <select id="new-template-category" bind:value={newCategory}>
                    {#each categories as cat (cat.id)}
                        <option value={cat.slug}>{categoryLabel(cat.slug)}</option>
                    {/each}
                </select>
                <p class="muted hint">Items matching this category will inherit the template's custom fields.</p>
            </div>
            <div class="preset-link-row">
                <span class="muted">Already have a community preset?</span>
                <button type="button" class="link" onclick={() => (scraperOpen = true)}>
                    Start from a scraper preset
                </button>
            </div>
        </div>
    {:else}
        <div class="stack">
            <div class="field">
                <div class="row-head">
                    <span>Custom fields for <em>{newName || 'this template'}</em></span>
                    <button type="button" class="link" onclick={() => {
                        if (!advancedOpen) syncJsonFromFields();
                        advancedOpen = !advancedOpen;
                    }}>{advancedOpen ? 'Use simple editor' : 'Advanced (JSON)'}</button>
                </div>

                {#if advancedOpen}
                    <textarea
                        rows="8"
                        bind:value={advancedJson}
                        onblur={syncFieldsFromJson}
                        spellcheck="false"
                        style="font-family:var(--mono,monospace);width:100%"
                    ></textarea>
                    <p class="muted hint">
                        JSON array of <code>&#123;key,label,type,required?,options?,default?&#125;</code>.
                        Allowed types: {FIELD_TYPES.join(', ')}.
                    </p>
                {:else}
                    {#if fields.length === 0}
                        <p class="muted" style="margin:.25rem 0 .5rem">No custom fields yet. Add one below.</p>
                    {:else}
                        <table class="fields">
                            <thead>
                                <tr>
                                    <th>Key</th>
                                    <th>Label</th>
                                    <th>Type</th>
                                    <th>Required</th>
                                    <th>Source</th>
                                    <th>Options</th>
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
                                                oninput={(e) => updateField(idx, { key: (e.target as HTMLInputElement).value })}
                                            />
                                        </td>
                                        <td>
                                            <input
                                                value={f.label}
                                                placeholder="Catalog #"
                                                oninput={(e) => updateField(idx, { label: (e.target as HTMLInputElement).value })}
                                            />
                                        </td>
                                        <td>
                                            <select
                                                value={f.type}
                                                onchange={(e) => updateField(idx, { type: (e.target as HTMLSelectElement).value as TemplateFieldType })}
                                            >
                                                {#each FIELD_TYPES as ft}
                                                    <option value={ft}>{ft}</option>
                                                {/each}
                                            </select>
                                        </td>
                                        <td style="text-align:center">
                                            <input
                                                type="checkbox"
                                                checked={f.required ?? false}
                                                onchange={(e) => updateField(idx, { required: (e.target as HTMLInputElement).checked })}
                                            />
                                        </td>
                                        <td>
                                            {#if f.type === 'select'}
                                                <select
                                                    value={f.select_source ?? 'static'}
                                                    onchange={(e) => updateField(idx, { select_source: (e.target as HTMLSelectElement).value as 'static' | 'dynamic' })}
                                                >
                                                    <option value="static">Static list</option>
                                                    <option value="dynamic">Dynamic from used values</option>
                                                </select>
                                            {:else if f.type === 'relation'}
                                                <select
                                                    value={f.relation_scope ?? 'same_collection'}
                                                    onchange={(e) => updateField(idx, { relation_scope: (e.target as HTMLSelectElement).value as 'same_collection' | 'any_collection' })}
                                                >
                                                    <option value="same_collection">Same collection</option>
                                                    <option value="any_collection">Any collection</option>
                                                </select>
                                            {:else}
                                                <span class="muted">&#x2014;</span>
                                            {/if}
                                        </td>
                                        <td>
                                            {#if f.type === 'select' && (f.select_source ?? 'static') === 'static'}
                                                <input
                                                    value={(f.options ?? []).join(', ')}
                                                    placeholder="A, B, C"
                                                    oninput={(e) => updateField(idx, {
                                                        options: (e.target as HTMLInputElement)
                                                            .value.split(',').map((s) => s.trim()).filter(Boolean)
                                                    })}
                                                />
                                            {:else if f.type === 'select'}
                                                <span class="muted">Auto from existing item values</span>
                                            {:else if f.type === 'relation'}
                                                <span class="muted">Resolved by item id</span>
                                            {:else}
                                                <span class="muted">&#x2014;</span>
                                            {/if}
                                        </td>
                                        <td>
                                            <Button variant="danger" size="sm" onclick={() => removeField(idx)}>×</Button>
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    {/if}
                    <button type="button" onclick={addField}>+ Add field</button>
                {/if}
            </div>
        </div>
    {/if}
</Modal>

<Modal
    bind:open={scraperOpen}
    title="Community scraper registry"
    width="52rem"
    onclose={() => (scraperOpen = false)}
>
    <p class="muted" style="margin:0 0 0.75rem">
        Curated, version-controlled presets contributed by the community.
        Importing a preset creates a matching template for this collection.
    </p>
    {#if registryEntries.length === 0}
        <p class="muted">No registry entries available.</p>
    {:else}
        <div class="registry-grid">
            {#each registryEntries as entry (entry.id)}
                <article class="registry-card">
                    <div class="registry-head">
                        <strong>{entry.name}</strong>
                        {#if entry.trusted}<span class="trusted-pill">Trusted</span>{/if}
                    </div>
                    <p class="muted" style="margin:0">{entry.description}</p>
                    <p class="muted" style="margin:0">
                        Provider: {entry.provider} &middot; Category: {categoryLabel(entry.category_slug)}
                    </p>
                    <div class="registry-actions">
                        <a href={entry.homepage} target="_blank" rel="noreferrer">Source</a>
                        {#if canEdit}
                            <button
                                type="button"
                                onclick={() => importRegistryEntry(entry)}
                                disabled={importingRegistryId === entry.id}
                            >{importingRegistryId === entry.id ? 'Importing&#x2026;' : 'Import preset'}</button>
                        {/if}
                    </div>
                </article>
            {/each}
        </div>
    {/if}
</Modal>

<style>
    .intro {
        margin-top: 0;
    }
    .toolbar {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin-bottom: 0.75rem;
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
    .hint {
        margin: 0.25rem 0 0;
        font-size: 0.85em;
    }
    .req {
        color: var(--danger, #c0392b);
    }
    .preset-link-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9em;
    }
    .name-cell {
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }
    .linked-pill {
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.05rem 0.4rem;
        border-radius: 999px;
        border: 1px solid color-mix(in srgb, var(--accent) 45%, transparent);
        color: var(--accent);
        background: color-mix(in srgb, var(--accent) 10%, transparent);
        width: fit-content;
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
    .registry-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 0.6rem;
    }
    .registry-card {
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.6rem;
        display: grid;
        gap: 0.35rem;
        background: color-mix(in srgb, var(--accent) 4%, var(--surface));
    }
    .registry-head {
        display: flex;
        justify-content: space-between;
        gap: 0.4rem;
        align-items: baseline;
    }
    .trusted-pill {
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.05rem 0.4rem;
        border-radius: 999px;
        border: 1px solid color-mix(in srgb, var(--success) 45%, transparent);
        color: var(--success);
        background: color-mix(in srgb, var(--success) 12%, transparent);
    }
    .registry-actions {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .scaffold-preview {
        margin-bottom: 1rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 0.75rem;
        background: color-mix(in srgb, var(--accent) 4%, var(--surface));
    }
    .scaffold-entry {
        border-bottom: 1px solid var(--border);
        padding: 0.4rem 0;
    }
    .scaffold-entry:last-child {
        border-bottom: none;
    }
    .scaffold-entry > summary {
        cursor: pointer;
        display: flex;
        align-items: baseline;
        gap: 0.6rem;
        list-style: none;
        padding: 0.25rem 0;
    }
    .scaffold-entry > summary::-webkit-details-marker { display: none; }
    .scaffold-entry > summary::before {
        content: '▸';
        font-size: 0.7em;
        color: var(--muted-text, #888);
        transition: transform 0.15s;
    }
    .scaffold-entry[open] > summary::before { content: '▾'; }
    .scaffold-entry .slug {
        font-size: 0.78em;
        color: var(--muted-text, #888);
    }
    .fields-preview {
        margin: 0.4rem 0 0.25rem 1rem;
        font-size: 0.88em;
        border-collapse: collapse;
        width: calc(100% - 1rem);
    }
    .fields-preview th,
    .fields-preview td {
        padding: 0.2rem 0.4rem;
        text-align: left;
        border-bottom: 1px solid var(--border);
    }
    .fields-preview thead th { font-weight: 600; }
</style>
