<script lang="ts">
    import { onMount, untrack } from 'svelte';
    import { page } from '$app/stores';
    import { _ } from 'svelte-i18n';
    import { api, ApiError, type Category, type Collection } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';
    import { Alert } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    let collections = $state<Collection[]>([]);
    let collectionId = $state('');
    let categories = $state<Category[]>([]);

    let mode = $state<'clz' | 'csv' | 'list' | 'restore'>('clz');

    // CLZ
    let clzFlavor = $state<'clz-movie' | 'clz-music' | 'clz-book' | 'clz-comic' | 'clz-game'>('clz-movie');
    let clzFile = $state<FileList | null>(null);

    // CSV
    let csvRoot = $state('movies');
    let csvLeaf = $state('movies.dvd');
    let csvFile = $state<FileList | null>(null);
    let csvMapping = $state(
        '{\n  "Title": "title",\n  "Subtitle": "subtitle",\n  "Year": "attr:year",\n  "Notes": "notes",\n  "Quantity": "quantity",\n  "Condition": "condition",\n  "Location": "location",\n  "Currency": "currency",\n  "Purchase price": "purchase_price",\n  "Current value": "current_value",\n  "Barcode": "id:barcode"\n}'
    );

    // List (plain titles)
    let listRoot = $state('movies');
    let listLeaf = $state('movies.dvd');
    let listText = $state('');
    let listFile = $state<FileList | null>(null);

    // Restore
    let restoreFile = $state<FileList | null>(null);

    let busy = $state(false);
    let result = $state('');
    let error = $state('');

    const roots = $derived(rootCategories(categories));
    const csvLeaves = $derived.by(() => {
        const r = categories.find((c) => c.slug === csvRoot);
        return r ? childrenOf(categories, r.id) : [];
    });
    const listLeaves = $derived.by(() => {
        const r = categories.find((c) => c.slug === listRoot);
        return r ? childrenOf(categories, r.id) : [];
    });

    $effect(() => {
        if (csvLeaves.length && !csvLeaves.some((l) => l.slug === untrack(() => csvLeaf))) {
            csvLeaf = csvLeaves[0].slug;
        }
    });
    $effect(() => {
        if (listLeaves.length && !listLeaves.some((l) => l.slug === untrack(() => listLeaf))) {
            listLeaf = listLeaves[0].slug;
        }
    });

    onMount(async () => {
        categories = await loadCategories();
        collections = await api.get<Collection[]>('/collections');
        const preselect = $page.url.searchParams.get('collection');
        if (preselect && collections.some((c) => c.id === preselect)) {
            collectionId = preselect;
        } else if (collections.length) {
            collectionId = collections[0].id;
        }
    });

    async function submit(e: Event) {
        e.preventDefault();
        error = '';
        result = '';
        busy = true;
        try {
            const fd = new FormData();
            let path = '';
            if (mode === 'clz') {
                if (!clzFile?.[0]) { error = $_('import_page.error_pick_file'); busy = false; return; }
                fd.set('collection_id', collectionId);
                fd.set('flavor', clzFlavor);
                fd.set('file', clzFile[0]);
                path = '/imports/clz';
            } else if (mode === 'csv') {
                if (!csvFile?.[0]) { error = $_('import_page.error_pick_file'); busy = false; return; }
                JSON.parse(csvMapping); // sanity
                fd.set('collection_id', collectionId);
                fd.set('category', csvLeaf);
                fd.set('mapping', csvMapping);
                fd.set('file', csvFile[0]);
                path = '/api/imports/csv';
            } else if (mode === 'list') {
                if (!listText.trim() && !listFile?.[0]) { error = $_('import_page.error_no_list'); busy = false; return; }
                fd.set('collection_id', collectionId);
                fd.set('category', listLeaf);
                if (listText.trim()) fd.set('titles', listText);
                if (listFile?.[0]) fd.set('file', listFile[0]);
                path = '/api/imports/list';
            } else {
                if (!restoreFile?.[0]) { error = $_('import_page.error_pick_file'); busy = false; return; }
                fd.set('file', restoreFile[0]);
                path = '/api/imports/restore';
            }
            const res = await fetch(path, {
                method: 'POST',
                body: fd,
                credentials: 'include'
            });
            const body = await res.text();
            if (!res.ok) {
                throw new ApiError(res.status, body, `HTTP ${res.status}: ${body}`);
            }
            result = body;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            busy = false;
        }
    }

    async function downloadBackup() {
        const res = await fetch('/api/imports/backup', { credentials: 'include' });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'tangible-backup.json';
        a.click();
        URL.revokeObjectURL(url);
    }

    async function downloadCsvTemplate() {
        const res = await fetch(`/api/imports/csv/template?category=${encodeURIComponent(csvLeaf)}`, {
            credentials: 'include'
        });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tangible-${csvLeaf.replace('.', '-')}-template.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    async function downloadCsvExport() {
        if (!collectionId) return;
        const res = await fetch(`/api/imports/csv/export?collection_id=${encodeURIComponent(collectionId)}`, {
            credentials: 'include'
        });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const label = collections.find((c) => c.id === collectionId)?.name ?? 'collection';
        const safe = label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
        const a = document.createElement('a');
        a.href = url;
        a.download = `tangible-${safe || 'collection'}-roundtrip.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
</script>

<h1>{$_('import_page.heading')}</h1>

<div class="card" style="margin-bottom: 1rem">
    <button class="secondary" onclick={downloadBackup}>{$_('import_page.download_backup_button')}</button>
    {#if collections.length}
        <div class="field" style="margin-top: .75rem">
            <label for="csv-export-collection">{$_('import_page.collection_csv_export_label')}</label>
            <div style="display:flex; gap:.5rem; flex-wrap:wrap; align-items:center">
                <select id="csv-export-collection" bind:value={collectionId}>
                    {#each collections as c}
                        <option value={c.id}>{c.name}</option>
                    {/each}
                </select>
                <button class="secondary" type="button" onclick={downloadCsvExport}>{$_('import_page.download_csv_button')}</button>
            </div>
        </div>
    {/if}
    <p class="muted" style="margin-top:.5rem">
        Includes collections, items, tags, contacts, loans &amp; share links. Photo files are not
        included; copy <code>data/photos/</code> separately.
    </p>
</div>

<div class="card">
    <div class="field">
        <div class="mode-cards" role="radiogroup" aria-label={$_('import_page.mode_label')}>
            <label class="mode-card" class:active={mode === 'clz'}>
                <input type="radio" bind:group={mode} value="clz" class="sr-only" />
                <Icon name="file-archive" size={20} />
                <span class="mode-name">{$_('import_page.mode_clz')}</span>
                <span class="mode-desc muted">{$_('import_page.mode_clz_desc')}</span>
            </label>
            <label class="mode-card" class:active={mode === 'csv'}>
                <input type="radio" bind:group={mode} value="csv" class="sr-only" />
                <Icon name="file-spreadsheet" size={20} />
                <span class="mode-name">{$_('import_page.mode_csv')}</span>
                <span class="mode-desc muted">{$_('import_page.mode_csv_desc')}</span>
            </label>
            <label class="mode-card" class:active={mode === 'list'}>
                <input type="radio" bind:group={mode} value="list" class="sr-only" />
                <Icon name="list" size={20} />
                <span class="mode-name">{$_('import_page.mode_list')}</span>
                <span class="mode-desc muted">{$_('import_page.mode_list_desc')}</span>
            </label>
            <label class="mode-card" class:active={mode === 'restore'}>
                <input type="radio" bind:group={mode} value="restore" class="sr-only" />
                <Icon name="database-backup" size={20} />
                <span class="mode-name">{$_('import_page.mode_restore')}</span>
                <span class="mode-desc muted">{$_('import_page.mode_restore_desc')}</span>
            </label>
        </div>
    </div>

    <form onsubmit={submit}>
        {#if mode !== 'restore'}
            <div class="field">
                <label for="import-collection">{$_('import_page.target_collection_label')}</label>
                <select id="import-collection" bind:value={collectionId} required>
                    {#each collections as c}
                        <option value={c.id}>{c.name}</option>
                    {/each}
                </select>
            </div>
        {/if}

        {#if mode === 'clz'}
            <div class="field">
                <label for="clz-flavor">{$_('import_page.clz_product_label')}</label>
                <select id="clz-flavor" bind:value={clzFlavor}>
                    <option value="clz-movie">{$_('import_page.clz_movie')}</option>
                    <option value="clz-music">{$_('import_page.clz_music')}</option>
                    <option value="clz-book">{$_('import_page.clz_book')}</option>
                    <option value="clz-comic">{$_('import_page.clz_comic')}</option>
                    <option value="clz-game">{$_('import_page.clz_game')}</option>
                </select>
            </div>
            <div class="field">
                <label for="clz-file">{$_('import_page.clz_file_label')}</label>
                <input id="clz-file" type="file" accept=".xml,application/xml" bind:files={clzFile} />
            </div>
        {:else if mode === 'csv'}
            <div class="field">
                <label for="csv-category">{$_('import_page.csv_category_label')}</label>
                <div class="select-pair">
                    <select id="csv-category" bind:value={csvRoot}>
                        {#each roots as r (r.id)}
                            <option value={r.slug}>{r.name}</option>
                        {/each}
                    </select>
                    <select bind:value={csvLeaf}>
                        {#each csvLeaves as l (l.id)}
                            <option value={l.slug}>{l.name}</option>
                        {/each}
                    </select>
                </div>
            </div>
            <div class="field">
                <button type="button" class="secondary" onclick={downloadCsvTemplate}>
                    {$_('import_page.csv_template_button')}
                </button>
                <p class="muted hint">
                    {$_('import_page.csv_template_hint')}
                </p>
            </div>
            <div class="field">
                <label for="csv-file">{$_('import_page.csv_file_label')}</label>
                <input id="csv-file" type="file" accept=".csv,text/csv" bind:files={csvFile} />
            </div>
            <div class="field">
                <label for="csv-mapping">{$_('import_page.csv_mapping_label')}</label>
                <textarea id="csv-mapping" rows="8" bind:value={csvMapping}></textarea>
                <p class="muted">
                    Targets: <code>title</code>, <code>subtitle</code>, <code>notes</code>,
                    <code>quantity</code>, <code>condition</code>, <code>currency</code>,
                    <code>location</code>, <code>category_slug</code>,
                    <code>ref:item_ref</code>, <code>ref:parent_ref</code>,
                    or <code>id:&lt;name&gt;</code> / <code>attr:&lt;name&gt;</code>.
                </p>
            </div>
        {:else if mode === 'list'}
            <div class="field">
                <label>{$_('import_page.list_category_label')}</label>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:.5rem">
                    <select bind:value={listRoot}>
                        {#each roots as r (r.id)}
                            <option value={r.slug}>{r.name}</option>
                        {/each}
                    </select>
                    <select bind:value={listLeaf}>
                        {#each listLeaves as l (l.id)}
                            <option value={l.slug}>{l.name}</option>
                        {/each}
                    </select>
                </div>
            </div>
            <div class="field">
                <label>{$_('import_page.list_text_label')}</label>
                <textarea
                    id="list-text"
                    rows="8"
                    placeholder={$_('import_page.list_text_placeholder')}
                    bind:value={listText}
                ></textarea>
                <p class="muted hint">
                    {$_('import_page.list_text_hint')}
                </p>
            </div>
            <div class="field">
                <label>{$_('import_page.list_file_label')}</label>
                <input type="file" accept=".txt,text/plain" bind:files={listFile} />
            </div>
        {:else}
            <div class="field">
                <label>{$_('import_page.restore_file_label')}</label>
                <input type="file" accept=".json,application/json" bind:files={restoreFile} />
            </div>
        {/if}

        <button type="submit" disabled={busy}>{busy ? $_('import_page.working_button') : $_('import_page.submit_button')}</button>
        {#if error}<Alert variant="danger" dismissible onclose={() => (error = '')}>{error}</Alert>{/if}
        {#if result}
            <Alert variant="success">
                {$_('import_page.success_message')}
                <details style="margin-top:0.5rem">
                    <summary style="cursor:pointer;font-size:0.8rem">{$_('import_page.show_details')}</summary>
                    <pre style="font-size:0.75rem;overflow:auto;max-height:12rem">{result}</pre>
                </details>
            </Alert>
        {/if}
    </form>
</div>

<style>
    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
    .mode-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem; }
    .mode-card {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 0.25rem;
        padding: 0.75rem;
        border: 2px solid var(--border);
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: border-color 0.15s, background 0.15s;
    }
    .mode-card:hover { border-color: var(--accent); }
    .mode-card.active { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, var(--surface)); }
    .mode-name { font-weight: 600; font-size: 0.9rem; }
    .mode-desc { font-size: 0.75rem; }
</style>
