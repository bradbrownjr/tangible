<script lang="ts">
    import { onMount } from 'svelte';
    import { _ } from 'svelte-i18n';
    import type { Category, Tag } from '$lib/api';

    interface Props {
        isFocused: boolean;
        roots: Category[];
        rootFilter: string;
        wantedFilter: 'all' | 'wanted' | 'owned';
        archivedFilter: 'active' | 'archived' | 'all';
        tags: Tag[];
        activeTagIds: string[];
        tagMode: 'all' | 'any';
        onchange: () => void;
    }

    let {
        isFocused,
        roots,
        rootFilter = $bindable(),
        wantedFilter = $bindable(),
        archivedFilter = $bindable(),
        tags,
        activeTagIds = $bindable(),
        tagMode = $bindable(),
        onchange,
    }: Props = $props();

    // Open by default on desktop (≥1024px), closed on mobile.
    let isOpen = $state(false);

    onMount(() => {
        isOpen = window.matchMedia('(min-width: 1024px)').matches;
    });

    function toggleTag(tagId: string) {
        if (activeTagIds.includes(tagId)) {
            activeTagIds = activeTagIds.filter((t) => t !== tagId);
        } else {
            activeTagIds = [...activeTagIds, tagId];
        }
        onchange();
    }

    function toggleMode() {
        tagMode = tagMode === 'all' ? 'any' : 'all';
        onchange();
    }

    function clearTags() {
        activeTagIds = [];
        onchange();
    }
</script>

<details class="advanced-filters" bind:open={isOpen}>
    <summary class="advanced-filters-toggle">{$_('collection.advanced_filters')}</summary>

    <div class="advanced-filters-body">
        {#if !isFocused}
            <select bind:value={rootFilter} onchange={onchange} title="Category filter">
                <option value="">{$_('collection.all_categories')}</option>
                {#each roots as r (r.id)}
                    <option value={r.slug}>{r.name}</option>
                {/each}
            </select>
        {/if}

        <select bind:value={wantedFilter} onchange={onchange} title="Wanted status">
            <option value="all">{$_('collection.filter_all_ownership')}</option>
            <option value="owned">{$_('collection.filter_owned')}</option>
            <option value="wanted">{$_('collection.filter_wanted')}</option>
        </select>

        <select bind:value={archivedFilter} onchange={onchange} title="Archived status">
            <option value="active">{$_('collection.filter_active')}</option>
            <option value="archived">{$_('collection.filter_archived')}</option>
            <option value="all">{$_('collection.filter_active_archived')}</option>
        </select>

        {#if tags.length}
            <div class="tag-row">
                {#each tags as t (t.id)}
                    <button
                        type="button"
                        class="tag-chip"
                        class:active={activeTagIds.includes(t.id)}
                        onclick={() => toggleTag(t.id)}
                    >{t.name}</button>
                {/each}
                {#if activeTagIds.length > 1}
                    <button type="button" class="tag-mode-toggle" onclick={toggleMode} title={$_('collection.tag_mode_toggle_title')}>
                        {tagMode === 'all' ? $_('collection.tag_mode_all') : $_('collection.tag_mode_any')}
                    </button>
                {/if}
                {#if activeTagIds.length}
                    <button type="button" class="tag-clear" onclick={clearTags}>{$_('collection.tag_filter_clear')}</button>
                {/if}
            </div>
        {/if}
    </div>
</details>

<style>
    .advanced-filters {
        margin-bottom: 0.75rem;
    }
    .advanced-filters-toggle {
        font-size: 0.8rem;
        color: var(--text-muted);
        cursor: pointer;
        user-select: none;
        list-style: none;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0.15rem 0;
    }
    .advanced-filters-toggle::-webkit-details-marker { display: none; }
    .advanced-filters-toggle::before {
        content: '▸';
        font-size: 0.7rem;
        transition: transform 0.15s;
    }
    details[open] .advanced-filters-toggle::before { transform: rotate(90deg); }
    .advanced-filters-body {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        padding-top: 0.5rem;
    }
    .tag-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.4rem;
        align-items: center;
    }
    .tag-chip {
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
        border: 1px solid var(--border-color, #ccc);
        background: none;
        font-size: 0.8rem;
        cursor: pointer;
        color: var(--text-muted, #555);
        transition: background 0.1s, color 0.1s;
    }
    .tag-chip.active {
        background: var(--accent, #5b8af5);
        color: #fff;
        border-color: var(--accent, #5b8af5);
    }
    .tag-mode-toggle {
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        border: 1px solid var(--accent, #5b8af5);
        background: none;
        font-size: 0.75rem;
        font-weight: 600;
        cursor: pointer;
        color: var(--accent, #5b8af5);
    }
    .tag-clear {
        background: none;
        border: none;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
        cursor: pointer;
        text-decoration: underline;
    }

    @media (min-width: 1024px) {
        .advanced-filters-body { padding-top: 0.5rem; }
    }
</style>
