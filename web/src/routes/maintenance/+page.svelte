<script lang="ts">
    import { onMount } from 'svelte';
    import { api, type DueAlert } from '$lib/api';
    import { _ } from 'svelte-i18n';

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

    function severityLabel(a: DueAlert): string {
        if (a.severity === 'critical') return $_('maintenance.overdue_label');
        return $_('maintenance.upcoming_label');
    }

    function daysLabel(isoDate: string | null): string {
        if (!isoDate) return '';
        const diff = Math.round((new Date(isoDate).getTime() - Date.now()) / 86400000);
        if (diff < 0) return `${Math.abs(diff)}d overdue`;
        if (diff === 0) return 'due today';
        return `in ${diff}d`;
    }

    const kindLabels = $derived<Record<string, string>>({
        maintenance_due: $_('maintenance.kind_maintenance_due'),
        chore_due: $_('maintenance.kind_chore_due'),
        item_use_by: $_('maintenance.kind_item_use_by'),
        item_expires: $_('maintenance.kind_item_expires'),
        lot_use_by: $_('maintenance.kind_lot_use_by'),
        low_stock: $_('maintenance.kind_low_stock'),
    });

    const grouped = $derived(
        alerts.reduce<Record<string, DueAlert[]>>((acc, a) => {
            const k = a.kind;
            if (!acc[k]) acc[k] = [];
            acc[k].push(a);
            return acc;
        }, {})
    );
</script>

<svelte:head><title>{$_('maintenance.title')}</title></svelte:head>

<div class="page-header">
    <h1>{$_('maintenance.title')}</h1>
    <p class="hint">{$_('maintenance.description')}</p>
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
    <button onclick={load}>{$_('maintenance.refresh_button')}</button>
</div>

{#if loading}
    <p class="loading">Loading…</p>
{:else if error}
    <p class="error">{error}</p>
{:else if alerts.length === 0}
    <p class="empty">{$_('maintenance.empty', { values: { days: withinDays } })}</p>
{:else}
    {#each Object.entries(grouped) as [kind, items]}
        <section class="group">
            <h2 class="group-title">{kindLabels[kind] ?? kind} ({items.length})</h2>
            <ul class="alert-list">
                {#each items as alert (alert.id)}
                    <li class="alert-card severity-{alert.severity}">
                        <div class="alert-main">
                            <span class="alert-title">{alert.title}</span>
                            {#if alert.due_at}
                                <span class="due-badge severity-{alert.severity}">
                                    {daysLabel(alert.due_at)}
                                </span>
                            {/if}
                            <span class="severity-tag">{severityLabel(alert)}</span>
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
                    </li>
                {/each}
            </ul>
        </section>
    {/each}
{/if}

<style>
    .page-header { margin-bottom: 1.5rem; }
    .hint { color: var(--color-muted, #666); margin-top: 0.25rem; }
    .filter-row { display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1.5rem; flex-wrap: wrap; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
    select { padding: 0.4rem 0.6rem; border: 1px solid var(--color-border, #ddd); border-radius: 4px; font-size: 0.875rem; }
    button { padding: 0.4rem 0.8rem; border: 1px solid var(--color-border, #ddd); border-radius: 4px; cursor: pointer; font-size: 0.875rem; background: var(--color-surface, #fff); }
    .group { margin-bottom: 2rem; }
    .group-title { font-size: 1rem; font-weight: 600; margin-bottom: 0.75rem; padding-bottom: 0.25rem; border-bottom: 1px solid var(--color-border, #ddd); }
    .alert-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.5rem; }
    .alert-card { padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid var(--color-border, #ddd); background: var(--color-surface, #fff); }
    .alert-card.severity-critical { border-color: var(--color-danger, #dc2626); background: color-mix(in srgb, var(--color-danger, #dc2626) 5%, transparent); }
    .alert-card.severity-warning { border-color: var(--color-warning, #f59e0b); background: color-mix(in srgb, var(--color-warning, #f59e0b) 5%, transparent); }
    .alert-main { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .alert-title { font-weight: 600; }
    .due-badge { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 9999px; }
    .due-badge.severity-critical { background: var(--color-danger-bg, #fee2e2); color: var(--color-danger, #dc2626); }
    .due-badge.severity-warning { background: var(--color-warning-bg, #fef3c7); color: var(--color-warning-text, #92400e); }
    .severity-tag { font-size: 0.75rem; color: var(--color-muted, #666); margin-left: auto; }
    .alert-detail { margin: 0.25rem 0 0; font-size: 0.8rem; color: var(--color-muted, #666); }
    .alert-links { margin-top: 0.5rem; display: flex; gap: 0.75rem; font-size: 0.8rem; }
    .alert-links a { color: var(--color-primary, #4f46e5); text-decoration: none; }
    .alert-links a:hover { text-decoration: underline; }
    .loading, .empty { text-align: center; color: var(--color-muted, #666); padding: 2rem; }
    .error { color: var(--color-danger, #dc2626); padding: 1rem; }
</style>
