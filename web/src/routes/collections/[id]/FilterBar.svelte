<script lang="ts">
    import { _ } from 'svelte-i18n';

    interface Props {
        search: string;
        viewMode: 'list' | 'grid';
        sortBy: 'sort_order' | 'title' | 'value' | 'acquired_at' | 'attr';
        sortDir: 'asc' | 'desc';
        sortAttr: string;
        onchange: () => void;
        searchInputEl?: HTMLInputElement;
    }

    let {
        search = $bindable(),
        viewMode = $bindable(),
        sortBy = $bindable(),
        sortDir = $bindable(),
        sortAttr = $bindable(),
        onchange,
        searchInputEl = $bindable(),
    }: Props = $props();
</script>

<div class="filter-bar">
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
        />
    {/if}
</div>

<style>
    .filter-bar {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .search-input {
        flex: 1;
        min-width: 140px;
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
</style>
