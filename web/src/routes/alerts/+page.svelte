<script lang="ts">
    import { onMount } from 'svelte';
    import { api, type DueAlert } from '$lib/api';
    import { _ } from 'svelte-i18n';
    import { EmptyState } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    let alerts = $state<DueAlert[]>([]);
    let loading = $state(true);
    let error = $state('');
    let withinDays = $state(30);

    async function load() {
        loading = true;
        error = '';
        try {
            alerts = await api.get<DueAlert[]>(`/alerts?within_days=${withinDays}`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    function daysLabel(isoDate: string | null): string {
        if (!isoDate) return '';
        const diff = Math.round((new Date(isoDate).getTime() - Date.now()) / 86400000);
        if (diff < 0) return $_('maintenance.days_overdue', { values: { days: Math.abs(diff) } });
        if (diff === 0) return $_('maintenance.due_today');
        return $_('maintenance.in_days', { values: { days: diff } });
    }

    const KIND_ICON: Record<string, string> = {
        maintenance_due: 'wrench',
        chore_due:       'sparkles',
        item_use_by:     'clock',
        item_expires:    'calendar-x',
        lot_use_by:      'clock',
        low_stock:       'package-x',
        task_due:        'check-circle',
    };

    const kindLabels = $derived<Record<string, string>>({
        maintenance_due: $_('maintenance.kind_maintenance_due'),
        chore_due:       $_('maintenance.kind_chore_due'),
        item_use_by:     $_('maintenance.kind_item_use_by'),
        item_expires:    $_('maintenance.kind_item_expires'),
        lot_use_by:      $_('maintenance.kind_lot_use_by'),
        low_stock:       $_('maintenance.kind_low_stock'),
        task_due:        $_('maintenance.kind_task_due'),
    });

    const sorted = $derived(
        [...alerts].sort((a, b) => {
            if (a.severity === 'critical' && b.severity !== 'critical') return -1;
            if (b.severity === 'critical' && a.severity !== 'critical') return 1;
            const da = a.due_at ? new Date(a.due_at).getTime() : Infinity;
            const db = b.due_at ? new Date(b.due_at).getTime() : Infinity;
            return da - db;
        })
    );

    const grouped = $derived(
        sorted.reduce<Record<string, DueAlert[]>>((acc, a) => {
            const k = a.kind;
            if (!acc[k]) acc[k] = [];
            acc[k].push(a);
            return acc;
        }, {})
    );
</script>

<svelte:head><title>{$_('alerts.page_title')} — Tangible</title></svelte:head>

<div class="page-header">
    <div class="page-title-row">
        <Icon name="bell" size={22} />
        <h1>{$_('alerts.page_title')}</h1>
    </div>
    <p class="muted">{$_('alerts.page_description')}</p>
</div>

<div class="filter-row">
    <label>
        {$_('maintenance.show_next_label')}
        <select bind:value={withinDays} onchange={load}>
            <option value={7}>{$_('maintenance.days_7')}</option>
            <option value={14}>{$_('maintenance.days_14')}</option>
            <option value={30}>{$_('maintenance.days_30')}</option>
            <option value={60}>{$_('maintenance.days_60')}</option>
            <option value={90}>{$_('maintenance.days_90')}</option>
            <option value={365}>{$_('maintenance.days_365')}</option>
        </select>
    </label>
    <button onclick={load}>
        <Icon name="arrow-up" size={14} />
        {$_('maintenance.refresh_button')}
    </button>
</div>

{#if loading}
    <EmptyState icon="loader" heading={$_('common.loading')} />
{:else if error}
    <p class="error">{error}</p>
{:else if alerts.length === 0}
    <EmptyState
        icon="party-popper"
        heading={$_('maintenance.empty', { values: { days: withinDays } })}
        body={$_('maintenance.all_clear')}
    />
{:else}
    {#each Object.entries(grouped) as [kind, items]}
        <section class="group">
            <h2 class="group-title">
                <Icon name={KIND_ICON[kind] ?? 'bell'} size={16} />
                {kindLabels[kind] ?? kind}
                <span class="group-count">{items.length}</span>
            </h2>
            <ul class="alert-list">
                {#each items as alert (alert.id)}
                    <li class="alert-card" class:severity-critical={alert.severity === 'critical'} class:severity-warning={alert.severity !== 'critical'}>
                        <div class="alert-left">
                            {#if alert.severity === 'critical'}
                                <Icon name="circle-alert" size={16} class="sev-icon sev-critical" />
                            {:else}
                                <Icon name="triangle-alert" size={16} class="sev-icon sev-warning" />
                            {/if}
                        </div>
                        <div class="alert-body">
                            <div class="alert-main">
                                <span class="alert-title">{alert.title}</span>
                                {#if alert.due_at}
                                    <span class="due-badge" class:critical={alert.severity === 'critical'}>
                                        <time datetime={alert.due_at}>{daysLabel(alert.due_at)}</time>
                                    </span>
                                {/if}
                            </div>
                            {#if alert.details}
                                <p class="alert-detail">{alert.details}</p>
                            {/if}
                            <div class="alert-links">
                                {#if alert.item_id}
                                    <a href="/collections/{alert.collection_id}?item={alert.item_id}">
                                        {$_('maintenance.view_item_link')}
                                    </a>
                                {/if}
                                <a href="/collections/{alert.collection_id}">{$_('maintenance.collection_link')}</a>
                                {#if kind === 'chore_due'}
                                    <a href="/collections/{alert.collection_id}/chores">{$_('maintenance.chores_link')}</a>
                                {/if}
                            </div>
                        </div>
                    </li>
                {/each}
            </ul>
        </section>
    {/each}
{/if}

<style>
    .page-header { margin-bottom: 1.25rem; }
    .page-title-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
    .page-title-row h1 { margin: 0; }

    .filter-row { display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .filter-row button { min-height: unset; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }

    .group { margin-bottom: 2rem; }
    .group-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.75rem;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid var(--border);
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .group-count {
        margin-left: auto;
        font-size: 0.75rem;
        font-weight: 400;
        color: var(--text-muted);
        background: var(--surface-2);
        padding: 0.1rem 0.5rem;
        border-radius: var(--radius-full);
    }

    .alert-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
    .alert-card {
        padding: 0.75rem 1rem;
        border-radius: var(--radius-md);
        border-left: 4px solid var(--border);
        background: var(--surface);
        display: flex;
        gap: 0.75rem;
        align-items: flex-start;
    }
    .alert-card.severity-critical {
        border-left-color: var(--danger);
        background: color-mix(in srgb, var(--danger) 5%, var(--surface));
    }
    .alert-card.severity-warning {
        border-left-color: var(--warning);
        background: color-mix(in srgb, var(--warning) 5%, var(--surface));
    }
    .alert-left { padding-top: 0.1rem; flex-shrink: 0; }
    :global(.sev-critical) { color: var(--danger); }
    :global(.sev-warning) { color: var(--warning); }
    .alert-body { flex: 1; min-width: 0; }
    .alert-main { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .alert-title { font-weight: 600; }
    .due-badge {
        font-size: 0.75rem;
        padding: 0.15rem 0.5rem;
        border-radius: var(--radius-full);
        background: color-mix(in srgb, var(--warning) 15%, transparent);
        color: var(--warning);
    }
    .due-badge.critical {
        background: color-mix(in srgb, var(--danger) 15%, transparent);
        color: var(--danger);
    }
    .alert-detail { margin: 0.25rem 0 0; font-size: 0.8rem; color: var(--text-muted); }
    .alert-links { margin-top: 0.5rem; display: flex; gap: 0.75rem; font-size: 0.8rem; align-items: center; flex-wrap: wrap; }
    .alert-links a { color: var(--accent); text-decoration: none; display: flex; align-items: center; gap: 0.2rem; }
    .alert-links a:hover { text-decoration: underline; }

    .error { color: var(--danger); }
</style>
