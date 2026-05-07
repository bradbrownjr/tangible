<script lang="ts">
    import { onMount } from 'svelte';
    import { _ } from 'svelte-i18n';
    import type { Snippet } from 'svelte';

    interface Props {
        /** Number of currently-active filters (shows badge when > 0). */
        activeCount?: number;
        /** Filter controls to render inside the collapsible body. */
        children?: Snippet;
        /** Optional actions (e.g. + Add button) rendered on the right of the header chip row. */
        actions?: Snippet;
    }

    let { activeCount = 0, children, actions }: Props = $props();

    let isOpen = $state(false);

    onMount(() => {
        isOpen = window.matchMedia('(min-width: 1024px)').matches;
    });
</script>

<div class="filters-panel">
    <div class="panel-header">
        <button
            type="button"
            class="filters-chip"
            class:has-active={activeCount > 0}
            onclick={() => (isOpen = !isOpen)}
            aria-expanded={isOpen}
        >
            {$_('filters.label')}{#if activeCount > 0}&thinsp;&middot;&thinsp;{activeCount}{/if}
            <span class="caret" aria-hidden="true">{isOpen ? '▴' : '▾'}</span>
        </button>
        {#if actions}
            <div class="panel-actions">
                {@render actions()}
            </div>
        {/if}
    </div>

    {#if isOpen && children}
        <div class="panel-body">
            {@render children()}
        </div>
    {/if}
</div>

<style>
    .filters-panel {
        margin-bottom: 0.75rem;
    }

    .panel-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        justify-content: space-between;
        margin-bottom: 0.25rem;
    }

    .filters-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.25rem 0.65rem;
        border-radius: 99px;
        border: 1px solid var(--border);
        background: var(--surface);
        font-size: 0.8rem;
        color: var(--text-muted);
        cursor: pointer;
        user-select: none;
        transition: background 0.12s, border-color 0.12s, color 0.12s;
        flex-shrink: 0;
    }

    .filters-chip:hover {
        border-color: var(--accent);
        color: var(--accent);
    }

    .filters-chip.has-active {
        background: color-mix(in srgb, var(--accent) 12%, var(--surface));
        border-color: color-mix(in srgb, var(--accent) 40%, transparent);
        color: var(--accent);
        font-weight: 600;
    }

    .caret {
        font-size: 0.65rem;
        opacity: 0.8;
    }

    .panel-actions {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-shrink: 0;
    }

    .panel-body {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        padding: 0.5rem 0 0.25rem;
        border-top: 1px solid var(--border);
    }

    @media (max-width: 640px) {
        .panel-body {
            flex-direction: column;
            align-items: stretch;
        }
    }
</style>
