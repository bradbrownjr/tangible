<script lang="ts">
    import { _ } from 'svelte-i18n';
    import { api } from '$lib/api';
    import type { Item } from '$lib/api';

    interface Props {
        item: Item | null;
        cid: string;
        collectionCreatorLabel: string | null;
        showCollectionSubtitle: boolean;
        isConsumable: (slug: string | null) => boolean;
        onSave: (id: string, payload: Record<string, unknown>) => Promise<void>;
        onClose: () => void;
    }

    let {
        item,
        cid,
        collectionCreatorLabel,
        showCollectionSubtitle,
        isConsumable,
        onSave,
        onClose,
    }: Props = $props();

    let editTitle = $state('');
    let editCreator = $state('');
    let editSubtitle = $state('');
    let editCondition = $state('');
    let editQuantity = $state(1);
    let editPurchasedAt = $state('');
    let editUseByDate = $state('');
    let editDateFrozen = $state('');
    let editDateOpened = $state('');
    let saving = $state(false);
    let conditionSuggestions = $state<string[]>([]);
    let creatorSuggestions = $state<string[]>([]);

    $effect(() => {
        if (item) {
            editTitle = item.title;
            editCreator = String(item.attrs?.creator ?? '');
            editSubtitle = item.subtitle ?? '';
            editCondition = item.condition ?? '';
            editQuantity = item.quantity;
            editPurchasedAt = item.purchased_at ? new Date(item.purchased_at).toISOString().slice(0, 16) : '';
            editUseByDate = item.use_by_date ? new Date(item.use_by_date).toISOString().slice(0, 16) : '';
            editDateFrozen = item.date_frozen ? new Date(item.date_frozen).toISOString().slice(0, 16) : '';
            editDateOpened = item.date_opened ? new Date(item.date_opened).toISOString().slice(0, 16) : '';
            saving = false;

            if (!conditionSuggestions.length) {
                api.get<string[]>(`/collections/${cid}/field-suggestions?field=condition`, true)
                    .then((v) => { conditionSuggestions = v; })
                    .catch(() => {});
            }
            if (collectionCreatorLabel && !creatorSuggestions.length) {
                api.get<string[]>(`/collections/${cid}/field-suggestions?field=creator`, true)
                    .then((v) => { creatorSuggestions = v; })
                    .catch(() => {});
            }
        }
    });

    async function save() {
        if (!item) return;
        saving = true;
        const attrsPayload: Record<string, string> = {};
        if (editCreator.trim()) attrsPayload.creator = editCreator.trim();
        const updatePayload: Record<string, unknown> = {
            title: editTitle.trim(),
            subtitle: editSubtitle.trim() || null,
            condition: editCondition.trim() || null,
            quantity: editQuantity,
            attrs: attrsPayload,
        };
        if (isConsumable(item.category_slug)) {
            updatePayload.purchased_at = editPurchasedAt ? new Date(editPurchasedAt).toISOString() : null;
            updatePayload.use_by_date = editUseByDate ? new Date(editUseByDate).toISOString() : null;
            updatePayload.date_frozen = editDateFrozen ? new Date(editDateFrozen).toISOString() : null;
            updatePayload.date_opened = editDateOpened ? new Date(editDateOpened).toISOString() : null;
        }
        try {
            await onSave(item.id, updatePayload);
        } finally {
            saving = false;
        }
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') onClose();
    }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
{#if item}
    <!-- Backdrop -->
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="panel-backdrop" onclick={onClose} aria-hidden="true"></div>

    <!-- Panel -->
    <div
        class="edit-panel"
        role="dialog"
        aria-modal="true"
        aria-label={$_('collection.edit_panel_title')}
        onkeydown={handleKeydown}
    >
        <div class="panel-header">
            <h2 class="panel-title">{item.title}</h2>
            <button type="button" class="panel-close" onclick={onClose} aria-label={$_('common.close')}>✕</button>
        </div>

        <div class="panel-body">
            {#if collectionCreatorLabel}
                <label class="field-label">
                    {collectionCreatorLabel}
                    <input bind:value={editCreator} placeholder={collectionCreatorLabel} class="edit-input" list="edit-creator-suggestions" />
                </label>
            {/if}

            <label class="field-label">
                {$_('collection.col_title')}
                <input bind:value={editTitle} placeholder={$_('collection.col_title')} class="edit-input" required />
            </label>

            {#if showCollectionSubtitle}
                <label class="field-label">
                    {$_('collection.subtitle_placeholder')}
                    <input bind:value={editSubtitle} placeholder={$_('collection.subtitle_placeholder')} class="edit-input" />
                </label>
            {/if}

            <div class="field-row">
                <label class="field-label">
                    {$_('collection.col_condition')}
                    <input bind:value={editCondition} placeholder={$_('collection.col_condition')} class="edit-input" list="edit-condition-suggestions" />
                </label>
                <label class="field-label field-label--sm">
                    {$_('collection.col_qty')}
                    <input type="number" bind:value={editQuantity} min="0" placeholder={$_('collection.col_qty')} class="edit-input" />
                </label>
            </div>

            {#if isConsumable(item.category_slug)}
                <div class="field-section-label">{$_('collection.consumable_dates_label')}</div>
                <div class="dates-grid">
                    <label class="field-label">
                        {$_('collection.consumable_purchased')}
                        <input type="datetime-local" bind:value={editPurchasedAt} class="edit-input" />
                    </label>
                    <label class="field-label">
                        {$_('collection.consumable_use_by')}
                        <input type="datetime-local" bind:value={editUseByDate} class="edit-input" />
                    </label>
                    <label class="field-label">
                        {$_('collection.consumable_frozen')}
                        <input type="datetime-local" bind:value={editDateFrozen} class="edit-input" />
                    </label>
                    <label class="field-label">
                        {$_('collection.consumable_opened')}
                        <input type="datetime-local" bind:value={editDateOpened} class="edit-input" />
                    </label>
                </div>
            {/if}
        </div>

        <div class="panel-footer">
            <button type="button" class="secondary" onclick={onClose} disabled={saving}>{$_('common.cancel')}</button>
            <button type="button" onclick={save} disabled={saving || !editTitle.trim()}>{saving ? $_('common.saving') : $_('common.save')}</button>
        </div>

        <datalist id="edit-condition-suggestions">
            <option value="New" />
            <option value="Mint" />
            <option value="Excellent" />
            <option value="Good" />
            <option value="Fair" />
            <option value="Poor" />
            {#each conditionSuggestions as s (s)}<option value={s} />{/each}
        </datalist>
        <datalist id="edit-creator-suggestions">
            {#each creatorSuggestions as s (s)}<option value={s} />{/each}
        </datalist>
    </div>
{/if}

<style>
    .panel-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        z-index: 200;
    }
    .edit-panel {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: min(100vw, 480px);
        z-index: 201;
        background: var(--surface);
        border-left: 1px solid var(--border);
        display: flex;
        flex-direction: column;
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.25);
    }
    .panel-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 1rem 1.25rem 0.75rem;
        border-bottom: 1px solid var(--border);
        flex-shrink: 0;
    }
    .panel-title {
        flex: 1;
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .panel-close {
        background: none;
        border: none;
        font-size: 1rem;
        cursor: pointer;
        color: var(--text-muted);
        padding: 0;
        min-width: var(--tap-min);
        min-height: var(--tap-min);
        line-height: 1;
        flex-shrink: 0;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .panel-close:hover { color: var(--text); }
    .panel-body {
        flex: 1;
        overflow-y: auto;
        padding: 1rem 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }
    .panel-footer {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        padding: 0.75rem 1.25rem;
        border-top: 1px solid var(--border);
        flex-shrink: 0;
        background: var(--surface);
    }
    .field-label {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
    }
    .field-label--sm { flex: 0 0 6rem; }
    .field-row {
        display: flex;
        gap: 0.75rem;
        align-items: flex-start;
    }
    .field-row .field-label:first-child { flex: 1; }
    .field-section-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--text-muted);
        margin-top: 0.25rem;
    }
    .dates-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.5rem;
    }
    .edit-input {
        width: 100%;
        box-sizing: border-box;
        padding: 0.35rem 0.5rem;
        font: inherit;
        font-size: 0.875rem;
    }

    @media (max-width: 639px) {
        .edit-panel {
            width: 100vw;
        }
    }
</style>
