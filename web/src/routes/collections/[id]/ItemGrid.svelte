<script lang="ts">
    import { _ } from 'svelte-i18n';
    import { IconButton } from '$lib/components';
    import ItemComments from '$lib/ItemComments.svelte';
    import PhotoGallery from '$lib/PhotoGallery.svelte';
    import type { Item } from '$lib/api';
    import { secondaryLine } from '$lib/itemDisplay';

    interface RelationEntry { key: string; label: string; targetId: string; }

    interface Props {
        items: Item[];
        canEdit: boolean;
        isFocused: boolean;
        selectedItemIds: string[];
        collectionCreatorLabel: string | null;
        currentUserId: string | undefined;
        formatValue: (i: Item) => string;
        displayValue: (i: Item) => number | null;
        relationEntries: (i: Item) => RelationEntry[];
        relationTitle: (targetId: string) => string;
        quickActionLabel: (slug: string | null) => (() => string) | null;
        isConsumable: (slug: string | null) => boolean;
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
        currentUserId,
        formatValue,
        displayValue,
        relationEntries,
        relationTitle,
        quickActionLabel,
        isConsumable,
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

<div class="item-grid">
    {#each items as i (i.id)}
        {@const secondary = secondaryLine(i)}
        <div class="item-card" class:depleted-card={i.depleted} class:wanted-card={i.wanted} class:archived-card={i.archived_at != null}>
            <div class="item-card-body">
                {#if canEdit}
                    <label class="select-chip">
                        <input
                            type="checkbox"
                            checked={selectedItemIds.includes(i.id)}
                            onchange={() => onToggleSelect(i.id)}
                        />
                        {$_('collection.item_select_label')}
                    </label>
                {/if}
                {#if !isFocused && i.category_slug}
                    <button type="button" class="category-badge filter-link" onclick={() => onFilterByCategory(i.category_slug!)}>{i.category_slug.split('.').at(-1) ?? i.category_slug}</button>
                {/if}
                {#if secondary}
                    <p class="item-creator"><button type="button" class="filter-link" onclick={() => onFilterBySearch(secondary)}>{secondary}</button></p>
                {/if}
                <p class="item-title">{i.title}</p>                <PhotoGallery itemId={i.id} {canEdit} compact />
                <ItemComments itemId={i.id} {currentUserId} canManage={canEdit} />
                {#if relationEntries(i).length}
                    <div class="relation-list">
                        {#each relationEntries(i) as rel (`${rel.key}:${rel.targetId}`)}
                            <div class="relation-card" title={rel.targetId}>
                                <span class="relation-label">{rel.label}</span>
                                <span class="relation-target">{relationTitle(rel.targetId)}</span>
                            </div>
                        {/each}
                    </div>
                {/if}
                <div class="item-meta">
                    {#if i.condition}<button type="button" class="filter-link" onclick={() => onFilterBySearch(i.condition!)}>{i.condition}</button>{/if}
                    {#if i.quantity > 1}<span>×{i.quantity}</span>{/if}
                    {#if displayValue(i) != null}<span>{formatValue(i)}</span>{/if}
                    {#if i.location_path && i.location_path.length}<button type="button" class="location-badge filter-link" title="Filter by location" onclick={() => onFilterBySearch(i.location_path!.at(-1)!)}>{i.location_path.join(' / ')}</button>{/if}
                    {#if i.depleted}<span class="depleted-badge">{$_('collection.badge_depleted')}</span>{/if}
                    {#if i.wanted}<span class="wanted-badge">{$_('collection.badge_wanted')}</span>{/if}
                    {#if i.archived_at}<span class="archived-badge">{$_('collection.badge_archived')}</span>{/if}
                    {#if i.flagged_at}<span class="flagged-badge" title={i.flagged_note ?? $_('collection.flag_for_review')}>{$_('collection.badge_flagged')}</span>{/if}
                    {#if isConsumable(i.category_slug)}
                        {#if i.use_by_date}<span class="date-badge use-by"><time datetime={i.use_by_date}>{$_('collection.badge_use_by', { values: { date: new Date(i.use_by_date).toLocaleDateString() } })}</time></span>{/if}
                        {#if i.date_opened}<span class="date-badge opened"><time datetime={i.date_opened}>{$_('collection.badge_opened', { values: { date: new Date(i.date_opened).toLocaleDateString() } })}</time></span>{/if}
                    {/if}
                </div>
            </div>
            {#if canEdit}
                <div class="item-card-actions">
                    <button type="button" class="secondary" onclick={() => onEdit(i)}>{$_('collection.item_edit')}</button>
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
                </div>
            {/if}
        </div>
    {/each}
</div>

<style>
    .item-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
        gap: 0.75rem;
    }
    .item-card {
        display: flex;
        flex-direction: column;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
    }
    .item-card-body {
        flex: 1;
        padding: 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        min-width: 0;
    }
    .item-card-actions {
        display: flex;
        gap: 0;
        border-top: 1px solid var(--border);
        align-items: stretch;
    }
    .item-card-actions button.secondary {
        flex: 1;
        border-radius: 0;
        font-size: 0.8rem;
        padding: 0.4rem;
        border: none;
        border-right: 1px solid var(--border);
    }
    .more-menu {
        position: relative;
        display: flex;
        align-items: center;
    }
    .more-dropdown {
        position: absolute;
        bottom: calc(100% + 4px);
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
    .category-badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--accent);
        background: color-mix(in srgb, var(--accent) 12%, transparent);
        border-radius: 4px;
        padding: 0.15em 0.45em;
        align-self: flex-start;
    }
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
    .select-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
    }
    .item-creator {
        font-size: 0.8rem;
        color: var(--text-muted, #888);
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .item-title {
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0;
        line-height: 1.3;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    .item-subtitle {
        font-size: 0.8rem;
        color: var(--text-muted, #888);
        margin: 0;
    }
    .item-meta {
        display: flex;
        gap: 0.5rem;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
        margin-top: auto;
        padding-top: 0.25rem;
        flex-wrap: wrap;
    }
    .location-badge {
        font-style: italic;
    }
    .relation-list {
        display: grid;
        gap: 0.3rem;
        margin-top: 0.2rem;
    }
    .relation-card {
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
    .depleted-card { opacity: 0.6; }
    .depleted-card .item-title {
        text-decoration: line-through;
        text-decoration-color: var(--danger, #c00);
    }
    .wanted-card { border-color: color-mix(in srgb, #2c7a7b 35%, var(--border)); }
    .archived-card { border-style: dashed; }
    .depleted-badge { color: var(--danger, #c00); font-weight: 600; }
    .wanted-badge { color: #2c7a7b; font-weight: 600; }
    .archived-badge { color: #666; font-weight: 600; }
    .flagged-badge {
        display: inline-flex;
        align-items: center;
        background: color-mix(in srgb, var(--warn, #c67a00) 18%, transparent);
        color: var(--warn, #c67a00);
        border: 1px solid color-mix(in srgb, var(--warn, #c67a00) 45%, transparent);
        border-radius: 999px;
        padding: 0.05rem 0.45rem;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .date-badge {
        font-size: 0.7rem;
        font-weight: 500;
        padding: 0.2em 0.4em;
        border-radius: 3px;
        background: color-mix(in srgb, currentColor 12%, transparent);
    }
    .date-badge.use-by { color: color-mix(in srgb, orange 70%, var(--fg)); }
    .date-badge.opened { color: color-mix(in srgb, #0066cc 70%, var(--fg)); }
</style>
