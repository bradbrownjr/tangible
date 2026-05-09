<script lang="ts">
    import { page } from '$app/state';
    import { goto } from '$app/navigation';
    import { setContext } from 'svelte';
    import { api, type Collection } from '$lib/api';
    import { me } from '$lib/session';
    import { _ } from 'svelte-i18n';
    import Icon from '$lib/Icon.svelte';
    import Modal from '$lib/components/Modal.svelte';
    import { ConfirmDialog } from '$lib/components';
    import TemplatesPage from './templates/+page.svelte';
    import LocationsPage from './locations/+page.svelte';
    import BundlesPage from './bundles/+page.svelte';
    import ChoresPage from './chores/+page.svelte';
    import MembersPage from './members/+page.svelte';

    let { children } = $props();

    const cid = $derived(page.params.id ?? '');
    let collection = $state<Collection | null>(null);

    // Filter panel state — shared with FilterBar.svelte via context so the toolbar
    // icon and the in-page chip both drive the same open/closed state.
    let filterOpen = $state(false);
    let filterActiveCount = $state(0);

    setContext('collectionFilterPanel', {
        get open() { return filterOpen; },
        toggle() { filterOpen = !filterOpen; },
        setActiveCount(n: number) { filterActiveCount = n; },
    });

    $effect(() => {
        if (!cid) return;
        // Reset filter panel whenever the user navigates to a different collection.
        filterOpen = false;
        filterActiveCount = 0;
        api.get<Collection>(`/collections/${cid}`).then(c => { collection = c; }).catch(() => {});
    });

    type Section = 'templates' | 'locations' | 'bundles' | 'chores' | 'members';
    let openSection = $state<Section | null>(null);

    function open(s: Section) { openSection = s; }
    function closePanel() { openSection = null; }

    let confirmDelete = $state(false);

    async function deleteCollectionConfirmed() {
        if (!collection) return;
        try {
            await api.delete(`/collections/${cid}`);
            confirmDelete = false;
            await goto('/');
        } catch (e) {
            // ignore — collection stays open
        }
    }

    const SECTIONS: Array<{ id: Section; icon: string; labelKey: string; width: string }> = [
        { id: 'templates', icon: 'file-cog',  labelKey: 'collection.tab_templates', width: '56rem' },
        { id: 'locations', icon: 'map-pin',   labelKey: 'collection.tab_locations', width: '52rem' },
        { id: 'bundles',   icon: 'box',       labelKey: 'collection.tab_bundles',   width: '48rem' },
        { id: 'chores',    icon: 'wrench',    labelKey: 'collection.tab_chores',    width: '52rem' },
        { id: 'members',   icon: 'users',     labelKey: 'collection.tab_members',   width: '44rem' },
    ];
</script>

<svelte:head>
    <title>Tangible · {collection?.name ?? $_('common.loading')}</title>
</svelte:head>

{#if collection?.description}<p class="muted">{collection.description}</p>{/if}

<div class="section-toolbar" role="toolbar" aria-label={$_('collection.section_toolbar_label')}>
    <!-- Search & filter toggle — drives the FiltersPanel in the item list below. -->
    <button
        type="button"
        class="toolbar-btn filter-toggle-btn"
        class:active={filterOpen}
        class:has-active={filterActiveCount > 0}
        title={$_('collection.toolbar_search_filter')}
        aria-label={$_('collection.toolbar_search_filter')}
        aria-expanded={filterOpen}
        onclick={() => { filterOpen = !filterOpen; }}
    >
        <Icon name="sliders-horizontal" size={17} />
        {#if filterActiveCount > 0 && !filterOpen}
            <span class="filter-badge" aria-hidden="true">{filterActiveCount}</span>
        {/if}
    </button>

    <span class="toolbar-divider" aria-hidden="true"></span>

    <a
        class="toolbar-btn export-btn"
        href="/import?collection={cid}"
        title={$_('collection.tab_import')}
        aria-label={$_('collection.tab_import')}
    >
        <Icon name="upload" size={17} />
    </a>
    <a
        class="toolbar-btn export-btn"
        href="/api/collections/{cid}/reports/insurance-export"
        download
        title={$_('collection.tab_export')}
        aria-label={$_('collection.tab_export')}
    >
        <Icon name="download" size={17} />
    </a>
    {#each SECTIONS as s (s.id)}
        <button
            type="button"
            class="toolbar-btn"
            class:active={openSection === s.id}
            title={$_(s.labelKey)}
            aria-label={$_(s.labelKey)}
            onclick={() => openSection === s.id ? closePanel() : open(s.id)}
        >
            <Icon name={s.icon} size={17} />
        </button>
    {/each}

    {#if collection?.my_role === 'owner'}
        <span class="toolbar-divider" aria-hidden="true"></span>
        <button
            type="button"
            class="toolbar-btn toolbar-btn--danger"
            title={$_('collection.delete_collection')}
            aria-label={$_('collection.delete_collection')}
            onclick={() => { confirmDelete = true; }}
        >
            <Icon name="trash-2" size={17} />
        </button>
    {/if}
</div>

{@render children()}

<ConfirmDialog
    open={confirmDelete}
    title={$_('collection.delete_collection_title')}
    variant="danger"
    confirmLabel={$_('collection.delete_collection_confirm')}
    message={$_('collection.delete_collection_text', { values: { name: collection?.name ?? '' } })}
    onconfirm={deleteCollectionConfirmed}
    oncancel={() => { confirmDelete = false; }}
/>

<!-- Section modals -->
{#each SECTIONS as s (s.id)}
    <Modal
        open={openSection === s.id}
        title={$_(s.labelKey)}
        width={s.width}
        onclose={closePanel}
    >
        {#snippet children()}
            {#if s.id === 'templates'}<TemplatesPage />{/if}
            {#if s.id === 'locations'}<LocationsPage />{/if}
            {#if s.id === 'bundles'}<BundlesPage />{/if}
            {#if s.id === 'chores'}<ChoresPage />{/if}
            {#if s.id === 'members'}<MembersPage />{/if}
        {/snippet}
    </Modal>
{/each}

<style>
    .section-toolbar {
        display: flex;
        gap: 0.25rem;
        padding: 0.25rem 0 0.75rem;
        margin-bottom: 0.25rem;
        flex-wrap: wrap;
    }

    .toolbar-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        min-height: unset;
        width: 2.2rem;
        height: 2.2rem;
        border-radius: var(--radius-sm);
        border: 1px solid var(--border);
        background: var(--surface);
        color: var(--text-muted);
        cursor: pointer;
        text-decoration: none;
        transition: color 0.12s, background 0.12s, border-color 0.12s;
        flex-shrink: 0;
    }

    .toolbar-btn:hover {
        color: var(--accent);
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 8%, var(--surface));
    }

    .toolbar-btn--danger:hover {
        color: var(--danger);
        border-color: var(--danger);
        background: color-mix(in srgb, var(--danger) 8%, var(--surface));
    }

    .toolbar-btn.active {
        color: var(--accent);
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 14%, var(--surface));
        font-weight: 600;
    }

    /* Export/import links on the left, section buttons on the right */
    .export-btn {
        margin-right: 0.25rem;
    }
    .export-btn + .export-btn {
        margin-right: 0.75rem;
    }

    /* Filter toggle button — shows accent fill when active filters exist (even closed). */
    .filter-toggle-btn {
        position: relative;
    }
    .filter-toggle-btn.has-active:not(.active) {
        border-color: color-mix(in srgb, var(--accent) 50%, transparent);
        color: var(--accent);
    }

    /* Small badge showing the active filter count, visible when panel is closed. */
    .filter-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        min-width: 1rem;
        height: 1rem;
        padding: 0 0.2rem;
        border-radius: 9999px;
        background: var(--accent);
        color: var(--accent-contrast);
        font-size: 0.6rem;
        font-weight: 700;
        line-height: 1rem;
        text-align: center;
        pointer-events: none;
    }

    /* Vertical rule separating filter toggle from the section/export buttons. */
    .toolbar-divider {
        width: 1px;
        align-self: stretch;
        background: var(--border);
        margin: 0.15rem 0.2rem;
        flex-shrink: 0;
    }

    @media (max-width: 640px) {
        .section-toolbar {
            gap: 0.2rem;
        }
        .toolbar-btn {
            width: 2rem;
            height: 2rem;
        }
    }
</style>

