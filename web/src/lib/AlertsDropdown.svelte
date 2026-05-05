<script lang="ts">
    import { onMount } from 'svelte';
    import { api } from '$lib/api';
    import { me } from '$lib/session';
    import { _ } from 'svelte-i18n';
    import Icon from './Icon.svelte';

    interface DueAlert {
        id: string;
        kind: string;
        severity: string;
        title: string;
        collection_id: string;
        item_id: string | null;
        due_at: string;
        details: string | null;
    }

    let open = $state(false);
    let alerts = $state<DueAlert[]>([]);
    let container: HTMLDivElement | undefined;

    async function load() {
        if (!$me) return;
        try {
            alerts = await api.get<DueAlert[]>('/alerts?within_days=30');
        } catch {
            alerts = [];
        }
    }

    onMount(() => {
        load();
        function handleClick(e: MouseEvent) {
            if (open && container && !container.contains(e.target as Node)) {
                open = false;
            }
        }
        function handleKey(e: KeyboardEvent) {
            if (e.key === 'Escape') open = false;
        }
        document.addEventListener('click', handleClick, true);
        document.addEventListener('keydown', handleKey);
        return () => {
            document.removeEventListener('click', handleClick, true);
            document.removeEventListener('keydown', handleKey);
        };
    });

    const critical = $derived(alerts.filter(a => a.severity === 'critical'));
    const warning = $derived(alerts.filter(a => a.severity !== 'critical'));
    const count = $derived(alerts.length);

    function formatDue(iso: string) {
        return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }
</script>

<div class="alerts-wrap" bind:this={container}>
    <button
        class="icon-btn"
        onclick={() => { open = !open; if (open) load(); }}
        title={$_('nav.alerts')}
        aria-label={$_('nav.alerts')}
        aria-expanded={open}
        aria-haspopup="true"
    >
        <Icon name="bell" size={18} />
        {#if count > 0}
            <span class="badge" aria-label="{count} {$_('nav.alerts')}">{count > 99 ? '99+' : count}</span>
        {/if}
    </button>

    {#if open}
        <div class="dropdown" role="dialog" aria-label={$_('nav.alerts')}>
            <div class="dropdown-header">
                <span>{$_('nav.alerts')}</span>
                {#if count > 0}<span class="count-badge">{count}</span>{/if}
            </div>
            {#if alerts.length === 0}
                <p class="empty">{$_('alerts.no_upcoming')}</p>
            {:else}
                <ul class="alert-list">
                    {#each critical as a (a.id)}
                        <li class="alert-item critical">
                            <Icon name="circle-alert" size={14} class="severity-icon severity-critical" />
                            <div class="alert-body">
                                <strong>{a.title}</strong>
                                {#if a.details}<span class="details">{a.details}</span>{/if}
                                <span class="due">{formatDue(a.due_at)}</span>
                            </div>
                        </li>
                    {/each}
                    {#each warning as a (a.id)}
                        <li class="alert-item warning">
                            <Icon name="triangle-alert" size={14} class="severity-icon severity-warning" />
                            <div class="alert-body">
                                <strong>{a.title}</strong>
                                {#if a.details}<span class="details">{a.details}</span>{/if}
                                <span class="due">{formatDue(a.due_at)}</span>
                            </div>
                        </li>
                    {/each}
                </ul>
            {/if}
            <div class="dropdown-footer">
                <a href="/maintenance" onclick={() => (open = false)}>{$_('alerts.view_all')}</a>
                <a href="/settings" onclick={() => (open = false)}>{$_('alerts.preferences_link')}</a>
            </div>
        </div>
    {/if}
</div>

<style>
    .alerts-wrap {
        position: relative;
    }
    .icon-btn {
        position: relative;
        background: transparent;
        border: none;
        color: var(--text);
        padding: 0.25rem;
        border-radius: 0.375rem;
        display: inline-flex;
        align-items: center;
        cursor: pointer;
    }
    .icon-btn:hover {
        background: color-mix(in srgb, var(--text) 8%, transparent);
    }
    .badge {
        position: absolute;
        top: -2px;
        right: -4px;
        min-width: 1rem;
        height: 1rem;
        padding: 0 0.25rem;
        font-size: 0.65rem;
        line-height: 1rem;
        text-align: center;
        border-radius: 999px;
        background: #dc2626;
        color: #fff;
        font-weight: 600;
        border: 2px solid var(--surface);
    }
    .dropdown {
        position: absolute;
        top: calc(100% + 0.5rem);
        right: 0;
        width: 22rem;
        max-height: 70vh;
        overflow-y: auto;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        z-index: 200;
        display: flex;
        flex-direction: column;
    }
    .dropdown-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.75rem 1rem;
        font-weight: 600;
        border-bottom: 1px solid var(--border);
        flex-shrink: 0;
    }
    .count-badge {
        display: inline-block;
        min-width: 1.2em;
        padding: 0 0.4em;
        font-size: 0.75rem;
        line-height: 1.4;
        text-align: center;
        border-radius: 999px;
        background: #dc2626;
        color: #fff;
        font-weight: 600;
    }
    .empty {
        padding: 1rem;
        color: var(--muted);
        margin: 0;
        font-size: 0.9rem;
    }
    .alert-list {
        list-style: none;
        margin: 0;
        padding: 0.25rem 0;
        overflow-y: auto;
    }
    .alert-item {
        display: flex;
        align-items: flex-start;
        gap: 0.6rem;
        padding: 0.6rem 1rem;
        border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
    }
    .alert-item:last-child {
        border-bottom: none;
    }
    :global(.severity-icon) {
        flex-shrink: 0;
        margin-top: 0.1rem;
    }
    :global(.severity-critical) { color: var(--danger); }
    :global(.severity-warning) { color: var(--warning); }
    .alert-body {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        flex: 1;
        min-width: 0;
    }
    .alert-body strong {
        font-size: 0.875rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .details {
        font-size: 0.8rem;
        color: var(--muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .due {
        font-size: 0.75rem;
        color: var(--muted);
    }
    .dropdown-footer {
        padding: 0.6rem 1rem;
        border-top: 1px solid var(--border);
        font-size: 0.875rem;
        flex-shrink: 0;
        display: flex;
        justify-content: space-between;
        gap: 1rem;
    }
    .dropdown-footer a {
        color: var(--accent);
        text-decoration: none;
    }
    .dropdown-footer a:hover {
        text-decoration: underline;
    }
    @media (max-width: 768px) {
        .dropdown {
            right: -0.5rem;
            width: min(22rem, calc(100vw - 1rem));
        }
    }
</style>
