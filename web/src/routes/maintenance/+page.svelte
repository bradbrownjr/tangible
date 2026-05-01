<script lang="ts">
    import { onMount } from 'svelte';
    import { api, type DueAlert } from '$lib/api';

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
        if (a.severity === 'critical') return 'Overdue';
        return 'Upcoming';
    }

    function daysLabel(isoDate: string | null): string {
        if (!isoDate) return '';
        const diff = Math.round((new Date(isoDate).getTime() - Date.now()) / 86400000);
        if (diff < 0) return `${Math.abs(diff)}d overdue`;
        if (diff === 0) return 'due today';
        return `in ${diff}d`;
    }

    const kindLabels: Record<string, string> = {
        maintenance_due: 'Maintenance',
        chore_due: 'Chore',
        item_use_by: 'Use by',
        item_expires: 'Expires',
        lot_use_by: 'Package',
        low_stock: 'Low stock'
    };

    const grouped = $derived(
        alerts.reduce<Record<string, DueAlert[]>>((acc, a) => {
            const k = a.kind;
            if (!acc[k]) acc[k] = [];
            acc[k].push(a);
            return acc;
        }, {})
    );
</script>

<svelte:head><title>Maintenance & alerts</title></svelte:head>

<div class="page-header">
    <h1>Maintenance &amp; alerts</h1>
    <p class="hint">Upcoming and overdue tasks, chores, expiry dates, and low stock.</p>
</div>

<div class="filter-row">
    <label>
        Show next
        <select bind:value={withinDays} onchange={load}>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
            <option value={365}>1 year</option>
        </select>
    </label>
    <button onclick={load}>Refresh</button>
</div>

{#if loading}
    <p class="loading">Loading…</p>
{:else if error}
    <p class="error">{error}</p>
{:else if alerts.length === 0}
    <p class="empty">No alerts in the next {withinDays} days.</p>
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
                                    View item
                                </a>
                            {/if}
                            <a href="/collections/{alert.collection_id}">Collection</a>
                            {#if kind === 'chore_due'}
                                <a href="/collections/{alert.collection_id}/chores">Chores</a>
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
