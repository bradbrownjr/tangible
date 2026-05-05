<script lang="ts">
    import { page } from '$app/state';
    import { api, type Collection } from '$lib/api';
    import { me } from '$lib/session';
    import { _ } from 'svelte-i18n';

    let { children } = $props();

    const cid = $derived(page.params.id ?? '');
    let collection = $state<Collection | null>(null);

    $effect(() => {
        if (!cid) return;
        api.get<Collection>(`/collections/${cid}`).then(c => { collection = c; }).catch(() => {});
    });

    const currentPath = $derived(page.url.pathname);

    // Exact match for /collections/{id}, prefix match for sub-routes
    function isActive(suffix: string): boolean {
        const href = `/collections/${cid}${suffix}`;
        if (suffix === '') return currentPath === href;
        return currentPath.startsWith(href);
    }
</script>

{#if collection}
    <h1>{collection.name}</h1>
    {#if collection.description}<p class="muted">{collection.description}</p>{/if}
{:else}
    <h1 class="skeleton-title" aria-label={$_('common.loading')}>&nbsp;</h1>
{/if}

<nav class="subnav" aria-label="Collection sections">
    <a class:tab-active={isActive('')} class="tab" href="/collections/{cid}"
        aria-current={isActive('') ? 'page' : undefined}>{$_('collection.tab_items')}</a>
    <a class:tab-active={isActive('/templates')} class="tab" href="/collections/{cid}/templates"
        aria-current={isActive('/templates') ? 'page' : undefined}>{$_('collection.tab_templates')}</a>
    <a class:tab-active={isActive('/locations')} class="tab" href="/collections/{cid}/locations"
        aria-current={isActive('/locations') ? 'page' : undefined}>{$_('collection.tab_locations')}</a>
    <a class:tab-active={isActive('/bundles')} class="tab" href="/collections/{cid}/bundles"
        aria-current={isActive('/bundles') ? 'page' : undefined}>{$_('collection.tab_bundles')}</a>
    <a class:tab-active={isActive('/chores')} class="tab" href="/collections/{cid}/chores"
        aria-current={isActive('/chores') ? 'page' : undefined}>{$_('collection.tab_chores')}</a>
    <a class:tab-active={isActive('/members')} class="tab" href="/collections/{cid}/members"
        aria-current={isActive('/members') ? 'page' : undefined}>{$_('collection.tab_members')}</a>
    <a class="tab" href="/import?collection={cid}">{$_('collection.tab_import')}</a>
    <a class="tab" href="/api/collections/{cid}/reports/insurance-export" download
        title="Download insurance-ready ZIP (CSV + photos)">{$_('collection.tab_export')}</a>
</nav>

{@render children()}

<style>
    h1 { margin-bottom: 0.2rem; }

    .skeleton-title {
        width: 12rem;
        background: var(--surface-2);
        border-radius: var(--radius-sm);
        min-height: 1.75rem;
    }

    .subnav {
        display: flex;
        gap: 0.25rem;
        padding: 0.5rem 0;
        border-bottom: 2px solid var(--border);
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        overflow-x: auto;
        scrollbar-width: none;
    }
    .subnav::-webkit-scrollbar { display: none; }

    .tab {
        flex-shrink: 0;
        padding: 0.35rem 0.75rem;
        border-radius: var(--radius-sm);
        font-size: 0.875rem;
        color: var(--text-muted);
        text-decoration: none;
        white-space: nowrap;
        border: none;
        background: transparent;
        cursor: pointer;
        transition: color 0.12s, background 0.12s;
    }
    .tab:hover {
        color: var(--text);
        background: color-mix(in srgb, var(--text) 6%, transparent);
    }
    .tab-active {
        color: var(--accent);
        font-weight: 600;
        background: color-mix(in srgb, var(--accent) 10%, transparent);
    }

    @media (max-width: 640px) {
        .subnav {
            gap: 0.15rem;
        }
        .tab {
            padding: 0.3rem 0.5rem;
            font-size: 0.8rem;
        }
    }
</style>
