<script lang="ts">
    import { _ } from 'svelte-i18n';
    import FiltersPanel from '$lib/components/FiltersPanel.svelte';
    import type { Category, Tag } from '$lib/api';

    interface Props {
        search: string;
        viewMode: 'list' | 'grid';
        sortBy: 'sort_order' | 'title' | 'value' | 'acquired_at' | 'attr';
        sortDir: 'asc' | 'desc';
        sortAttr: string;
        onchange: () => void;
        searchInputEl?: HTMLInputElement;
        /* Advanced filter props (merged from AdvancedFilters.svelte) */
        isFocused?: boolean;
        roots?: Category[];
        rootFilter?: string;
        wantedFilter?: 'all' | 'wanted' | 'owned';
        archivedFilter?: 'active' | 'archived' | 'all';
        tags?: Tag[];
        activeTagIds?: string[];
        tagMode?: 'all' | 'any';
    }

    let {
        search = $bindable(),
        viewMode = $bindable(),
        sortBy = $bindable(),
        sortDir = $bindable(),
        sortAttr = $bindable(),
        onchange,
        searchInputEl = $bindable(),
        isFocused = false,
        roots = [],
        rootFilter = $bindable(''),
        wantedFilter = $bindable('all' as 'all' | 'wanted' | 'owned'),
        archivedFilter = $bindable('active' as 'active' | 'archived' | 'all'),
        tags = [],
        activeTagIds = $bindable([] as string[]),
        tagMode = $bindable('all' as 'all' | 'any'),
    }: Props = $props();

    let activeCount = $derived(
        (search.trim() ? 1 : 0) +
        (sortBy !== 'sort_order' ? 1 : 0) +
        (rootFilter ? 1 : 0) +
        (wantedFilter !== 'all' ? 1 : 0) +
        (archivedFilter !== 'active' ? 1 : 0) +
        (activeTagIds.length > 0 ? 1 : 0)
    );

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

<FiltersPanel {activeCount}>
    {#snippet children()}
        <input
            bind:this={searchInputEl}
            bind:value={search}
            placeholder={$_('collection.search_placeholder')}
            oninput={onchange}
            class="search-input"
        />

        <div class="view-toggle" role="group" aria-label="View mode">
            <button
                type="button"
                class="toggle-btn"
                class:active={viewMode === 'list'}
                onclick={() => (viewMode = 'list')}
                title={$_('collection.view_list')}
                aria-label={$_('collection.view_list')}
            >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <rect x="0" y="2" width="16" height="2" rx="1"/>
                    <rect x="0" y="7" width="16" height="2" rx="1"/>
                    <rect x="0" y="12" width="16" height="2" rx="1"/>
                </svg>
            </button>
            <button
                type="button"
                class="toggle-btn"
                class:active={viewMode === 'grid'}
                onclick={() => (viewMode = 'grid')}
                title={$_('collection.view_grid')}
                aria-label={$_('collection.view_grid')}
            >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <rect x="0" y="0" width="7" height="7" rx="1"/>
                    <rect x="9" y="0" width="7" height="7" rx="1"/>
                    <rect x="0" y="9" width="7" height="7" rx="1"/>
                    <rect x="9" y="9" width="7" height="7" rx="1"/>
                </svg>
            </button>
        </div>

        <select bind:value={sortBy} onchange={onchange} title="Sort by">
            <option value="title">{$_('collection.sort_title')}</option>
            <option value="sort_order">{$_('collection.sort_custom')}</option>
            <option value="value">{$_('collection.sort_value')}</option>
            <option value="acquired_at">{$_('collection.sort_acquired')}</option>
            <option value="attr">{$_('collection.sort_attr')}</option>
        </select>

        <select bind:value={sortDir} onchange={onchange} title="Sort direction">
            <option value="asc">{$_('collection.sort_asc')}</option>
            <option value="desc">{$_('collection.sort_desc')}</option>
        </select>

        {#if sortBy === 'attr'}
            <input
                bind:value={sortAttr}
                placeholder={$_('collection.sort_attr_key_placeholder')}
                title="Custom field key"
                onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onchange(); } }}
                onblur={onchange}
                class="sort-attr-input"
            />
        {/if}

        <!-- Advanced filter controls (was AdvancedFilters.svelte) -->
        <div class="advanced-row">
            {#if !isFocused && roots.length}
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
    {/snippet}
</FiltersPanel>

<style>
    .search-input {
        flex: 1;
        min-width: 140px;
    }
    .sort-attr-input {
        min-width: 8rem;
    }
    .view-toggle {
        display: flex;
        gap: 0;
        border: 1px solid var(--border);
        border-radius: 6px;
        overflow: hidden;
        flex-shrink: 0;
    }
    .toggle-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 0.6rem;
        min-height: var(--tap-min);
        background: var(--surface);
        border: none;
        border-radius: 0;
        color: var(--text-muted, #888);
        cursor: pointer;
    }
    .toggle-btn:hover { color: var(--accent); }
    .toggle-btn.active {
        background: var(--accent);
        color: var(--accent-fg, white);
    }

    /* Override global width:100% so selects stay inline in the flex row. */
    select {
        width: auto;
        min-width: 7rem;
        flex-shrink: 0;
    }

    /* Advanced filter controls sit on their own wrapping row */
    .advanced-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        width: 100%;
        padding-top: 0.25rem;
        border-top: 1px solid color-mix(in srgb, var(--border) 60%, transparent);
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
</style>

