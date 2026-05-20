<script lang="ts">
    import { _ } from 'svelte-i18n';
    import type { ItemTemplate } from '$lib/api';

    interface Props {
        creatorLabel: string | null;
        subtitleLabel: string | null;
        activeTemplate: ItemTemplate | null;
        newAttrs: Record<string, unknown>;
        newRoot: string;
        newLeaf: string;
        newQuery: string;
        newCreator: string;
        newSubtitle: string;
        scraping: boolean;
        error: string;
        detected: 'url' | 'isbn' | 'ean' | 'title';
        onSubmit: (e: Event) => void;
        onLookup: () => void;
        onBarcodeChange: (e: Event) => void;
    }

    let {
        creatorLabel,
        subtitleLabel,
        activeTemplate,
        newAttrs,
        newRoot = $bindable(),
        newLeaf = $bindable(),
        newQuery = $bindable(),
        newCreator = $bindable(),
        newSubtitle = $bindable(),
        scraping,
        error,
        detected,
        onSubmit,
        onLookup,
        onBarcodeChange,
    }: Props = $props();

    let barcodeImageInput: HTMLInputElement | undefined;

    let creatorInput: HTMLInputElement | undefined = $state();
    let titleInput: HTMLInputElement | undefined;
    let subtitleInput: HTMLInputElement | undefined = $state();

    const templateFields = $derived(
        (activeTemplate?.fields ?? []).filter(f => f.type !== 'relation')
    );
    const hasMoreOptions = $derived(
        !!(creatorLabel || subtitleLabel || templateFields.length)
    );

    export function focusTitle() {
        queueMicrotask(() => (creatorLabel ? creatorInput : titleInput)?.focus());
    }
</script>

<form onsubmit={onSubmit} class="add-form">
    <input
        bind:this={barcodeImageInput}
        type="file"
        accept="image/*"
        style="display:none"
        onchange={onBarcodeChange}
    />
    <div class="add-row">
        <input
            id="addq"
            bind:this={titleInput}
            bind:value={newQuery}
            placeholder={$_('collection.item_title_placeholder')}
            autocomplete="off"
            class="title-field"
            onkeydown={(e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    onSubmit(e);
                }
            }}
        />
        {#if detected !== 'title' && newQuery.trim()}
            <button type="button" onclick={onLookup} disabled={scraping}>
                {scraping ? $_('collection.looking_up_button') : $_('collection.lookup_button', { values: { type: detected.toUpperCase() } })}
            </button>
        {/if}
        <button type="button" class="secondary" onclick={() => barcodeImageInput?.click()} disabled={scraping}>
            {$_('collection.scan_image_button')}
        </button>
        <button type="submit" disabled={scraping || !newQuery.trim()}>{$_('collection.add_button')}</button>
    </div>

    {#if hasMoreOptions}
        <details class="more-options" open={templateFields.length > 0}>
            <summary>{$_('common.more_options')}</summary>
            <div class="more-options-grid">
                {#if creatorLabel}
                    <input
                        bind:this={creatorInput}
                        bind:value={newCreator}
                        placeholder={creatorLabel}
                        autocomplete="off"
                        class="creator-field"
                    />
                {/if}
                {#if subtitleLabel}
                    <input
                        bind:this={subtitleInput}
                        bind:value={newSubtitle}
                        placeholder={subtitleLabel}
                        autocomplete="off"
                        class="subtitle-field"
                    />
                {/if}
                {#each templateFields as field (field.key)}
                    <label class="template-field" class:required={field.required}>
                        <span class="field-label">{field.label}{field.required ? ' *' : ''}</span>
                        {#if field.type === 'boolean'}
                            <input
                                type="checkbox"
                                checked={Boolean(newAttrs[field.key])}
                                onchange={(e) => { newAttrs[field.key] = (e.currentTarget as HTMLInputElement).checked; }}
                            />
                        {:else if field.type === 'number'}
                            <input
                                type="number"
                                value={newAttrs[field.key] != null ? String(newAttrs[field.key]) : ''}
                                placeholder={field.help ?? ''}
                                oninput={(e) => {
                                    const v = (e.currentTarget as HTMLInputElement).value;
                                    newAttrs[field.key] = v === '' ? undefined : Number(v);
                                }}
                            />
                        {:else if field.type === 'date'}
                            <input
                                type="date"
                                value={newAttrs[field.key] != null ? String(newAttrs[field.key]) : ''}
                                oninput={(e) => { newAttrs[field.key] = (e.currentTarget as HTMLInputElement).value || undefined; }}
                            />
                        {:else if field.type === 'select'}
                            <select
                                value={newAttrs[field.key] != null ? String(newAttrs[field.key]) : ''}
                                onchange={(e) => { newAttrs[field.key] = (e.currentTarget as HTMLSelectElement).value || undefined; }}
                            >
                                <option value="">—</option>
                                {#each field.options ?? [] as opt}
                                    <option value={opt}>{opt}</option>
                                {/each}
                            </select>
                        {:else}
                            <input
                                type={field.type === 'url' ? 'url' : 'text'}
                                value={newAttrs[field.key] != null ? String(newAttrs[field.key]) : ''}
                                placeholder={field.help ?? ''}
                                oninput={(e) => { newAttrs[field.key] = (e.currentTarget as HTMLInputElement).value || undefined; }}
                            />
                        {/if}
                    </label>
                {/each}
            </div>
        </details>
    {/if}
    {#if error}<p class="error">{error}</p>{/if}
</form>

<style>
    .add-form {
        margin: 1rem 0 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .add-row {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .creator-field {
        flex: 1 1 150px;
        min-width: 120px;
        max-width: 210px;
    }
    .title-field {
        flex: 2 1 180px;
        min-width: 140px;
    }
    .subtitle-field {
        flex: 2 1 180px;
        min-width: 140px;
    }
    .more-options {
        margin-top: 0.5rem;
        border: 1px solid var(--border);
        border-radius: var(--radius-md, 8px);
        background: var(--surface);
    }
    .more-options > summary {
        padding: 0.5rem 0.75rem;
        font-size: 0.875rem;
        color: var(--text-muted);
        cursor: pointer;
        user-select: none;
        list-style: none;
    }
    .more-options > summary::-webkit-details-marker { display: none; }
    .more-options > summary::before { content: '+ '; }
    .more-options[open] > summary::before { content: '- '; }
    .more-options-grid {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        padding: 0.75rem;
        border-top: 1px solid var(--border);
    }
    .template-field {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        flex: 1 1 160px;
        min-width: 120px;
    }
    .template-field.required .field-label {
        font-weight: 600;
    }
    .field-label {
        font-size: 0.78rem;
        color: var(--text-muted);
        user-select: none;
    }
    .template-field input,
    .template-field select {
        width: 100%;
    }
    .template-field input[type='checkbox'] {
        width: auto;
        align-self: flex-start;
    }
</style>
