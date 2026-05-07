<script lang="ts">
    import { page } from '$app/state';
    import { api, type Collection } from '$lib/api';
    import { me } from '$lib/session';
    import { _ } from 'svelte-i18n';
    import Icon from '$lib/Icon.svelte';
    import Modal from '$lib/components/Modal.svelte';
    import TemplatesPage from './templates/+page.svelte';
    import LocationsPage from './locations/+page.svelte';
    import BundlesPage from './bundles/+page.svelte';
    import ChoresPage from './chores/+page.svelte';
    import MembersPage from './members/+page.svelte';

    let { children } = $props();

    const cid = $derived(page.params.id ?? '');
    let collection = $state<Collection | null>(null);

    $effect(() => {
        if (!cid) return;
        api.get<Collection>(`/collections/${cid}`).then(c => { collection = c; }).catch(() => {});
    });

    type Section = 'templates' | 'locations' | 'bundles' | 'chores' | 'members';
    let openSection = $state<Section | null>(null);

    function open(s: Section) { openSection = s; }
    function closePanel() { openSection = null; }

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
</div>

{@render children()}

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

