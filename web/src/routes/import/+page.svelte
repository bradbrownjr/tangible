<script lang="ts">
    import { onMount } from 'svelte';
    import { api, ApiError, type Category, type Collection } from '$lib/api';
    import { childrenOf, loadCategories, rootCategories } from '$lib/categories';

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
        if (csvLeaves.length && !csvLeaves.some((l) => l.slug === csvLeaf)) {
            csvLeaf = csvLeaves[0].slug;
        }
    });
    $effect(() => {
        if (listLeaves.length && !listLeaves.some((l) => l.slug === listLeaf)) {
            listLeaf = listLeaves[0].slug;
        }
    });

    onMount(async () => {
        categories = await loadCategories();
        collections = await api.get<Collection[]>('/collections');
        if (collections.length) collectionId = collections[0].id;
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
                if (!clzFile?.[0]) throw new Error('Pick a file');
                fd.set('collection_id', collectionId);
                fd.set('flavor', clzFlavor);
                fd.set('file', clzFile[0]);
                path = '/imports/clz';
            } else if (mode === 'csv') {
                if (!csvFile?.[0]) throw new Error('Pick a file');
                JSON.parse(csvMapping); // sanity
                fd.set('collection_id', collectionId);
                fd.set('category', csvLeaf);
                fd.set('mapping', csvMapping);
                fd.set('file', csvFile[0]);
                path = '/api/imports/csv';
            } else if (mode === 'list') {
                if (!listText.trim() && !listFile?.[0])
                    throw new Error('Paste a list or attach a .txt file');
                fd.set('collection_id', collectionId);
                fd.set('category', listLeaf);
                if (listText.trim()) fd.set('titles', listText);
                if (listFile?.[0]) fd.set('file', listFile[0]);
                path = '/api/imports/list';
            } else {
                if (!restoreFile?.[0]) throw new Error('Pick a file');
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
        a.download = 'covet-backup.json';
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
        a.download = `covet-${csvLeaf.replace('.', '-')}-template.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
</script>

<h1>Import / Backup</h1>

<div class="card" style="margin-bottom: 1rem">
    <button class="secondary" onclick={downloadBackup}>Download JSON backup</button>
    <p class="muted" style="margin-top:.5rem">
        Includes collections, items, tags, contacts, loans &amp; share links. Photo files are not
        included; copy <code>data/photos/</code> separately.
    </p>
</div>

<div class="card">
    <div class="field">
        <label>Mode</label>
        <select bind:value={mode}>
            <option value="clz">CLZ XML import</option>
            <option value="csv">Generic CSV import</option>
            <option value="list">List of titles (paste or .txt)</option>
            <option value="restore">Restore JSON backup</option>
        </select>
    </div>

    <form onsubmit={submit}>
        {#if mode !== 'restore'}
            <div class="field">
                <label>Target collection</label>
                <select bind:value={collectionId} required>
                    {#each collections as c}
                        <option value={c.id}>{c.name}</option>
                    {/each}
                </select>
            </div>
        {/if}

        {#if mode === 'clz'}
            <div class="field">
                <label>CLZ product</label>
                <select bind:value={clzFlavor}>
                    <option value="clz-movie">Movie Collector</option>
                    <option value="clz-music">Music Collector</option>
                    <option value="clz-book">Book Collector</option>
                    <option value="clz-comic">Comic Collector</option>
                    <option value="clz-game">Game Collector</option>
                </select>
            </div>
            <div class="field">
                <label>XML export file</label>
                <input type="file" accept=".xml,application/xml" bind:files={clzFile} />
            </div>
        {:else if mode === 'csv'}
            <div class="field">
                <label>Category</label>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:.5rem">
                    <select bind:value={csvRoot}>
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
                    Download CSV template
                </button>
                <p class="muted hint">
                    Fill in the template, then upload it below. The default mapping
                    matches the template's headers.
                </p>
            </div>
            <div class="field">
                <label>CSV file</label>
                <input type="file" accept=".csv,text/csv" bind:files={csvFile} />
            </div>
            <div class="field">
                <label>Column mapping (JSON)</label>
                <textarea rows="8" bind:value={csvMapping}></textarea>
                <p class="muted">
                    Targets: <code>title</code>, <code>subtitle</code>, <code>notes</code>,
                    <code>quantity</code>, <code>condition</code>, <code>currency</code>,
                    <code>location</code>, or <code>id:&lt;name&gt;</code> /
                    <code>attr:&lt;name&gt;</code>.
                </p>
            </div>
        {:else if mode === 'list'}
            <div class="field">
                <label>Category</label>
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
                <label for="list-text">Paste titles (one per line)</label>
                <textarea
                    id="list-text"
                    rows="8"
                    placeholder={'The Matrix\nPulp Fiction\nBlade Runner'}
                    bind:value={listText}
                ></textarea>
                <p class="muted hint">
                    Each non-blank line becomes a new item. Lines starting with
                    <code>#</code> are skipped. Flesh out the details later from the
                    collection screen.
                </p>
            </div>
            <div class="field">
                <label>Or attach a .txt file</label>
                <input type="file" accept=".txt,text/plain" bind:files={listFile} />
            </div>
        {:else}
            <div class="field">
                <label>Backup JSON file</label>
                <input type="file" accept=".json,application/json" bind:files={restoreFile} />
            </div>
        {/if}

        <button type="submit" disabled={busy}>{busy ? 'Working…' : 'Submit'}</button>
        {#if error}<p class="error">{error}</p>{/if}
        {#if result}<pre class="success">{result}</pre>{/if}
    </form>
</div>
