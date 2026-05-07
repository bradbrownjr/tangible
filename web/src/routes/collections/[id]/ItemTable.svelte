<script lang="ts">
    import { _ } from 'svelte-i18n';
    import { IconButton } from '$lib/components';
    import type { Item } from '$lib/api';
    import { secondaryLine } from '$lib/itemDisplay';

    interface RelationEntry { key: string; label: string; targetId: string; }

    interface Props {
        items: Item[];
        canEdit: boolean;
        isFocused: boolean;
        selectedItemIds: string[];
        collectionCreatorLabel: string | null;
        showCollectionSubtitle: boolean;
        formatValue: (i: Item) => string;
        relationEntries: (i: Item) => RelationEntry[];
        relationTitle: (targetId: string) => string;
        quickActionLabel: (slug: string | null) => (() => string) | null;
        isConsumable: (slug: string | null) => boolean;
        onSelectAll: (checked: boolean) => void;
        onToggleSelect: (id: string) => void;
        onEdit: (item: Item) => void;
        onQuickAction: (item: Item) => void;
        onDuplicate: (item: Item) => void;
        onToggleDepleted: (item: Item) => void;
        onToggleWanted: (item: Item) => void;
        onToggleFlag: (item: Item) => void;
        onArchive: (item: Item) => void;
        onDelete: (item: Item) => void;
        onFilterByCategory: (slug: string) => void;
        onFilterBySearch: (value: string) => void;
    }

    let {
        items,
        canEdit,
        isFocused,
        selectedItemIds,
        collectionCreatorLabel,
        showCollectionSubtitle,
        formatValue,
        relationEntries,
        relationTitle,
        quickActionLabel,
        isConsumable,
        onSelectAll,
        onToggleSelect,
        onEdit,
        onQuickAction,
        onDuplicate,
        onToggleDepleted,
        onToggleWanted,
        onToggleFlag,
        onArchive,
        onDelete,
        onFilterByCategory,
        onFilterBySearch,
    }: Props = $props();

    let openMenuId = $state<string | null>(null);

    $effect(() => {
        const close = () => { openMenuId = null; };
        document.addEventListener('click', close);
        return () => document.removeEventListener('click', close);
    });
</script>

<div class="table-wrap">
<table>
    <thead>
        <tr>
            {#if canEdit}
                <th style="width:1%">
                    <input
                        type="checkbox"
                        checked={items.length > 0 && selectedItemIds.length === items.length}
                        onchange={(e) => onSelectAll((e.target as HTMLInputElement).checked)}
                    />
                </th>
            {/if}
            {#if !isFocused}<th>{$_('collection.col_category')}</th>{/if}
            {#if collectionCreatorLabel}<th>{collectionCreatorLabel}</th>{/if}
            <th>{$_('collection.col_title')}</th>
            {#if showCollectionSubtitle}<th>{$_('collection.subtitle_placeholder')}</th>{/if}
            <th>{$_('collection.col_qty')}</th>
            <th>{$_('collection.col_condition')}</th>
            <th>{$_('collection.col_value')}</th>
            {#if canEdit}<th></th>{/if}
        </tr>
    </thead>
    <tbody>
        {#each items as i (i.id)}
            {@const sec = secondaryLine(i)}
            <tr
                id="item-{i.id}"
                class:depleted-row={i.depleted}
                class:wanted-row={i.wanted}
                class:archived-row={i.archived_at != null}
            >
                {#if canEdit}
                    <td>
                        <input
                            type="checkbox"
                            checked={selectedItemIds.includes(i.id)}
                            onchange={() => onToggleSelect(i.id)}
                        />
                    </td>
                {/if}
                {#if !isFocused}
                    <td class="muted">
                        {#if i.category_slug}
                            <button type="button" class="filter-link" onclick={() => onFilterByCategory(i.category_slug!)}>{i.category_slug}</button>
                        {/if}
                    </td>
                {/if}
                {#if collectionCreatorLabel}
                    <td class="muted">
                        {#if sec}
                            <button type="button" class="filter-link" onclick={() => onFilterBySearch(sec)}>{sec}</button>
                        {/if}
                    </td>
                {/if}
                <td>
                    {i.title}
                    {#if !collectionCreatorLabel && !showCollectionSubtitle}
                        {@const sec = secondaryLine(i)}
                        {#if sec}<span class="muted"> · {sec}</span>{/if}
                    {:else if i.subtitle && !showCollectionSubtitle}<span class="muted"> · {i.subtitle}</span>{/if}
                    {#if i.flagged_at}
                        <span class="flagged-inline" title={i.flagged_note ?? $_('collection.flag_for_review')}>{$_('collection.badge_flagged')}</span>
                    {/if}
                    {#if i.wanted}
                        <span class="wanted-inline" title="Marked as wanted / not currently owned">{$_('collection.badge_wanted')}</span>
                    {/if}
                    {#if i.archived_at}
                        <span class="archived-inline" title={i.disposition_type ?? 'archived'}>{$_('collection.badge_archived')}</span>
                    {/if}
                    {#if relationEntries(i).length}
                        <div class="relation-inline-list">
                            {#each relationEntries(i) as rel (`${rel.key}:${rel.targetId}`)}
                                <div class="relation-inline-card" title={rel.targetId}>
                                    <span class="relation-label">{rel.label}</span>
                                    <span class="relation-target">{relationTitle(rel.targetId)}</span>
                                </div>
                            {/each}
                        </div>
                    {/if}
                </td>
                {#if showCollectionSubtitle}<td class="muted">{i.subtitle ?? ''}</td>{/if}
                <td>{i.quantity}</td>
                <td>{i.condition ?? ''}</td>
                <td class="muted">{formatValue(i)}</td>
                {#if canEdit}
                    <td class="row-actions">
                        <button class="secondary" onclick={() => onEdit(i)}>{$_('collection.item_edit')}</button>
                        <div
                            class="more-menu"
                            role="none"
                            onclick={(e) => e.stopPropagation()}
                        >
                            <IconButton
                                name="more-horizontal"
                                label={$_('collection.more_actions')}
                                btnSize="sm"
                                onclick={(e) => { e.stopPropagation(); openMenuId = openMenuId === i.id ? null : i.id; }}
                            />
                            {#if openMenuId === i.id}
                                <div class="more-dropdown" role="menu">
                                    {#if quickActionLabel(i.category_slug)}
                                        <button type="button" role="menuitem" onclick={() => { onQuickAction(i); openMenuId = null; }} disabled={i.archived_at != null}>{quickActionLabel(i.category_slug)!()}</button>
                                    {/if}
                                    <button type="button" role="menuitem" onclick={() => { onDuplicate(i); openMenuId = null; }} disabled={i.archived_at != null}>{$_('collection.item_duplicate')}</button>
                                    <button type="button" role="menuitem" onclick={() => { onToggleDepleted(i); openMenuId = null; }} disabled={i.archived_at != null}>{i.depleted ? $_('collection.item_in_stock') : $_('collection.item_depleted')}</button>
                                    <button type="button" role="menuitem" onclick={() => { onToggleWanted(i); openMenuId = null; }} disabled={i.archived_at != null}>{i.wanted ? $_('collection.item_owned') : $_('collection.item_wanted')}</button>
                                    <button type="button" role="menuitem" onclick={() => { onToggleFlag(i); openMenuId = null; }} disabled={i.archived_at != null}>{i.flagged_at ? $_('collection.item_unflag') : $_('collection.item_flag')}</button>
                                    <button type="button" role="menuitem" onclick={() => { onArchive(i); openMenuId = null; }}>{i.archived_at ? $_('collection.item_restore') : $_('collection.item_archive')}</button>
                                    <hr class="menu-divider" />
                                    <button type="button" role="menuitem" class="menu-danger" onclick={() => { onDelete(i); openMenuId = null; }}>{$_('collection.item_delete')}</button>
                                </div>
                            {/if}
                        </div>
                    </td>
                {/if}
            </tr>
        {/each}
    </tbody>
</table>
</div>

<style>
    .table-wrap {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    th, td {
        padding: 0.45rem 0.5rem;
        text-align: left;
        border-bottom: 1px solid var(--border);
        font-size: 0.875rem;
    }
    th {
        font-weight: 600;
        font-size: 0.8rem;
        color: var(--text-muted);
    }
    .row-actions {
        white-space: nowrap;
        display: flex;
        gap: 0.35rem;
        align-items: center;
    }
    .more-menu {
        position: relative;
        display: inline-flex;
    }
    .more-dropdown {
        position: absolute;
        top: calc(100% + 4px);
        right: 0;
        min-width: 160px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        z-index: 100;
        padding: 0.25rem 0;
        display: flex;
        flex-direction: column;
    }
    .more-dropdown button {
        background: none;
        border: none;
        text-align: left;
        padding: 0.4rem 0.8rem;
        font-size: 0.85rem;
        cursor: pointer;
        color: var(--text);
        border-radius: 0;
    }
    .more-dropdown button:hover { background: var(--surface-2); }
    .more-dropdown button:disabled { opacity: 0.4; cursor: not-allowed; }
    .menu-divider { border: none; border-top: 1px solid var(--border); margin: 0.2rem 0; }
    .menu-danger { color: var(--danger) !important; }
    .filter-link {
        background: none;
        border: none;
        padding: 0;
        font: inherit;
        cursor: pointer;
        color: inherit;
        text-align: left;
    }
    .filter-link:hover { text-decoration: underline; opacity: 0.8; }
    .depleted-row td {
        opacity: 0.55;
        text-decoration: line-through;
        text-decoration-color: var(--danger, #c00);
    }
    .wanted-row td { background: color-mix(in srgb, #2c7a7b 8%, transparent); }
    .archived-row td {
        opacity: 0.75;
        background: color-mix(in srgb, #666 8%, transparent);
    }
    .flagged-inline {
        margin-left: 0.4rem;
        font-size: 0.72rem;
        font-weight: 600;
        color: var(--warn, #c67a00);
    }
    .wanted-inline {
        margin-left: 0.4rem;
        font-size: 0.72rem;
        font-weight: 600;
        color: #2c7a7b;
    }
    .archived-inline {
        margin-left: 0.4rem;
        font-size: 0.72rem;
        font-weight: 600;
        color: #666;
    }
    .relation-inline-list {
        display: grid;
        gap: 0.2rem;
        margin-top: 0.3rem;
        max-width: 32rem;
    }
    .relation-inline-card {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 0.45rem;
        align-items: baseline;
        border: 1px solid var(--border);
        background: color-mix(in srgb, var(--accent) 6%, var(--surface));
        border-radius: 6px;
        padding: 0.2rem 0.4rem;
    }
    .relation-label {
        font-size: 0.72rem;
        color: var(--text-muted, #888);
        white-space: nowrap;
    }
    .relation-target {
        font-size: 0.8rem;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
