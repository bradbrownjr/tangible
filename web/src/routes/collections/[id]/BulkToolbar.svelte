<script lang="ts">
    import { _ } from 'svelte-i18n';
    import type { Contact, Tag } from '$lib/api';

    interface LocationOption { id: string; label: string; }

    interface Props {
        selectedCount: number;
        busy: boolean;
        tags: Tag[];
        locationOptions: LocationOption[];
        contacts: Contact[];
        selectedBulkTagId: string;
        bulkMoveLocationId: string;
        selectedBulkContactId: string;
        bulkLoanDueAt: string;
        onSelectAll: () => void;
        onClearSelection: () => void;
        onBulkDepleted: () => void;
        onBulkInStock: () => void;
        onBulkWanted: () => void;
        onBulkOwned: () => void;
        onBulkArchive: () => void;
        onBulkRestore: () => void;
        onBulkAddTag: () => void;
        onBulkRemoveTag: () => void;
        onBulkMoveLocation: () => void;
        onBulkClearLocation: () => void;
        onBulkLend: () => void;
        onBulkDelete: () => void;
    }

    let {
        selectedCount,
        busy,
        tags,
        locationOptions,
        contacts,
        selectedBulkTagId = $bindable(),
        bulkMoveLocationId = $bindable(),
        selectedBulkContactId = $bindable(),
        bulkLoanDueAt = $bindable(),
        onSelectAll,
        onClearSelection,
        onBulkDepleted,
        onBulkInStock,
        onBulkWanted,
        onBulkOwned,
        onBulkArchive,
        onBulkRestore,
        onBulkAddTag,
        onBulkRemoveTag,
        onBulkMoveLocation,
        onBulkClearLocation,
        onBulkLend,
        onBulkDelete,
    }: Props = $props();

    const hasItems = $derived(selectedCount > 0);
</script>

{#if selectedCount > 0}
<div class="bulk-toolbar">
    <span class="bulk-count muted">{$_('collection.selected_count', { values: { count: selectedCount } })}</span>

    <div class="bulk-group">
        <button type="button" class="secondary sm" onclick={onSelectAll} disabled={busy}>{$_('collection.select_visible')}</button>
        <button type="button" class="secondary sm" onclick={onClearSelection} disabled={!hasItems || busy}>{$_('collection.clear_selection')}</button>
    </div>

    <div class="bulk-group">
        <span class="group-label">{$_('collection.bulk_group_status')}</span>
        <button type="button" class="secondary sm" onclick={onBulkDepleted} disabled={!hasItems || busy}>{$_('collection.bulk_depleted')}</button>
        <button type="button" class="secondary sm" onclick={onBulkInStock} disabled={!hasItems || busy}>{$_('collection.bulk_in_stock')}</button>
        <button type="button" class="secondary sm" onclick={onBulkWanted} disabled={!hasItems || busy}>{$_('collection.bulk_wanted')}</button>
        <button type="button" class="secondary sm" onclick={onBulkOwned} disabled={!hasItems || busy}>{$_('collection.bulk_owned')}</button>
        <button type="button" class="secondary sm" onclick={onBulkArchive} disabled={!hasItems || busy}>{$_('collection.bulk_archive')}</button>
        <button type="button" class="secondary sm" onclick={onBulkRestore} disabled={!hasItems || busy}>{$_('collection.bulk_restore')}</button>
    </div>

    <div class="bulk-group">
        <span class="group-label">{$_('collection.bulk_group_tags')}</span>
        <select bind:value={selectedBulkTagId} disabled={busy || tags.length === 0} title="Tag for bulk tagging">
            <option value="">{$_('collection.tag_dropdown')}</option>
            {#each tags as t (t.id)}
                <option value={t.id}>{t.name}</option>
            {/each}
        </select>
        <button type="button" class="secondary sm" onclick={onBulkAddTag} disabled={!hasItems || !selectedBulkTagId || busy}>{$_('collection.bulk_add_tag')}</button>
        <button type="button" class="secondary sm" onclick={onBulkRemoveTag} disabled={!hasItems || !selectedBulkTagId || busy}>{$_('collection.bulk_remove_tag')}</button>
    </div>

    <div class="bulk-group">
        <span class="group-label">{$_('collection.bulk_group_location')}</span>
        <select bind:value={bulkMoveLocationId} disabled={busy || locationOptions.length === 0} title="Bulk location move">
            <option value="">{$_('collection.location_dropdown')}</option>
            {#each locationOptions as opt (opt.id)}
                <option value={opt.id}>{opt.label}</option>
            {/each}
        </select>
        <button type="button" class="secondary sm" onclick={onBulkMoveLocation} disabled={!hasItems || !bulkMoveLocationId || busy}>{$_('collection.bulk_move_location')}</button>
        <button type="button" class="secondary sm" onclick={onBulkClearLocation} disabled={!hasItems || busy}>{$_('collection.bulk_clear_location')}</button>
    </div>

    <div class="bulk-group">
        <span class="group-label">{$_('collection.bulk_group_lend')}</span>
        <select bind:value={selectedBulkContactId} disabled={busy || contacts.length === 0} title="Contact for bulk lend">
            <option value="">{$_('collection.contact_dropdown')}</option>
            {#each contacts as c (c.id)}
                <option value={c.id}>{c.name}</option>
            {/each}
        </select>
        <input type="datetime-local" bind:value={bulkLoanDueAt} title="Bulk lend due date" disabled={busy} />
        <button type="button" class="secondary sm" onclick={onBulkLend} disabled={!hasItems || !selectedBulkContactId || busy}>{$_('collection.bulk_lend')}</button>
    </div>

    <button type="button" class="danger sm" onclick={onBulkDelete} disabled={!hasItems || busy}>{$_('collection.bulk_delete')}</button>
</div>
{/if}

<style>
    .bulk-toolbar {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 50;
        padding: 0.6rem 1rem;
        background: var(--surface, #1a1d29);
        border-top: 1px solid var(--border, #333);
        box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.25);
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        max-height: 50vh;
        overflow-y: auto;
    }
    .bulk-count {
        font-size: 0.875rem;
        font-weight: 600;
        flex-shrink: 0;
    }
    .bulk-group {
        display: flex;
        gap: 0.35rem;
        align-items: center;
        flex-wrap: wrap;
        padding: 0 0.5rem;
        border-left: 1px solid var(--border);
    }
    .bulk-group:first-of-type {
        border-left: none;
        padding-left: 0;
    }
    .group-label {
        font-size: 0.72rem;
        color: var(--text-muted);
        white-space: nowrap;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .bulk-toolbar select,
    .bulk-toolbar input[type="datetime-local"] {
        max-width: 12rem;
        flex: 0 1 auto;
        font-size: 0.8rem;
    }
    button.sm {
        font-size: 0.8rem;
        padding: 0 0.6rem;
        min-height: var(--tap-min);
    }
</style>
