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
    let tab = $state<'alerts' | 'chores'>('alerts');
    let showConfetti = $state(false);

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
    };

    const kindLabels = $derived<Record<string, string>>({
        maintenance_due: $_('maintenance.kind_maintenance_due'),
        chore_due:       $_('maintenance.kind_chore_due'),
        item_use_by:     $_('maintenance.kind_item_use_by'),
        item_expires:    $_('maintenance.kind_item_expires'),
        lot_use_by:      $_('maintenance.kind_lot_use_by'),
        low_stock:       $_('maintenance.kind_low_stock'),
    });

    // All alerts sorted: critical (overdue) first, then by due_at ascending
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

    // Chores tab: only chore_due alerts, sorted by due_at
    const choreAlerts = $derived(
        sorted.filter(a => a.kind === 'chore_due')
    );

    function launchConfetti() {
        showConfetti = true;
        setTimeout(() => { showConfetti = false; }, 2500);
    }
</script>

<svelte:head><title>{$_('tasks.title')}</title></svelte:head>

{#if showConfetti}
    <div class="confetti-overlay" aria-hidden="true">
        {#each { length: 24 } as _, i}
            <span class="confetti-piece" style="--delay:{(i * 0.11).toFixed(2)}s; --x:{(Math.sin(i * 2.39) * 50 + 50).toFixed(0)}%; --hue:{(i * 15) % 360}deg"></span>
        {/each}
    </div>
{/if}

<div class="page-header">
    <div class="page-title-row">
        <Icon name="calendar-clock" size={22} />
        <h1>{$_('tasks.title')}</h1>
    </div>
    <p class="muted">{$_('tasks.description')}</p>
</div>

<div class="tab-bar" role="tablist">
    <button
        role="tab"
        aria-selected={tab === 'alerts'}
        class="tab-btn"
        class:active={tab === 'alerts'}
        onclick={() => (tab = 'alerts')}
    >
        <Icon name="triangle-alert" size={15} />
        {$_('tasks.tab_alerts')}
    </button>
    <button
        role="tab"
        aria-selected={tab === 'chores'}
        class="tab-btn"
        class:active={tab === 'chores'}
        onclick={() => (tab = 'chores')}
    >
        <Icon name="sparkles" size={15} />
        {$_('tasks.tab_chores')}
        {#if choreAlerts.length > 0}
            <span class="tab-badge">{choreAlerts.length}</span>
        {/if}
    </button>
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
{:else if tab === 'alerts'}
    <!-- ── Alerts tab ── -->
    {#if alerts.length === 0}
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
{:else}
    <!-- ── Chores tab ── -->
    {#if choreAlerts.length === 0}
        <EmptyState
            icon="calendar-check"
            heading={$_('tasks.chores_empty', { values: { days: withinDays } })}
            body={$_('tasks.chores_all_clear')}
        />
    {:else}
        <p class="tab-hint">{$_('tasks.chores_hint')}</p>
        <ul class="alert-list">
            {#each choreAlerts as alert (alert.id)}
                <li class="alert-card chore-card" class:severity-critical={alert.severity === 'critical'} class:severity-warning={alert.severity !== 'critical'}>
                    <div class="alert-left">
                        <Icon name="sparkles" size={16} class="sev-icon {alert.severity === 'critical' ? 'sev-critical' : 'sev-warning'}" />
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
                            <a href="/collections/{alert.collection_id}/chores">
                                <Icon name="sparkles" size={12} />
                                {$_('tasks.manage_chores_link')}
                            </a>
                            <a href="/collections/{alert.collection_id}">{$_('maintenance.collection_link')}</a>
                        </div>
                    </div>
                    <div class="chore-actions">
                        <button
                            class="done-btn"
                            title={$_('tasks.mark_done_tooltip')}
                            onclick={launchConfetti}
                        >
                            <Icon name="calendar-check" size={16} />
                            <span class="sr-only">{$_('tasks.mark_done_tooltip')}</span>
                        </button>
                    </div>
                </li>
            {/each}
        </ul>
    {/if}
{/if}

<style>
    .page-header { margin-bottom: 1.25rem; }
    .page-title-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
    .page-title-row h1 { margin: 0; }

    /* Tabs */
    .tab-bar {
        display: flex;
        gap: 0.25rem;
        border-bottom: 2px solid var(--border);
        margin-bottom: 1.25rem;
    }
    .tab-btn {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        background: none;
        border: none;
        padding: 0.5rem 1rem;
        cursor: pointer;
        font-size: 0.9rem;
        color: var(--text-muted);
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0;
        transition: color 0.15s;
    }
    .tab-btn:hover { color: var(--text); }
    .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }
    .tab-badge {
        background: var(--danger);
        color: #fff;
        font-size: 0.7rem;
        padding: 0.05rem 0.4rem;
        border-radius: var(--radius-full);
        font-weight: 700;
    }

    .filter-row { display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1.5rem; flex-wrap: wrap; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }

    .tab-hint { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.75rem; }

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

    /* Chore card done button */
    .chore-actions { display: flex; align-items: center; }
    .done-btn {
        background: none;
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 0.35rem 0.5rem;
        cursor: pointer;
        color: var(--text-muted);
        transition: color 0.15s, border-color 0.15s, background 0.15s;
    }
    .done-btn:hover {
        color: var(--success);
        border-color: var(--success);
        background: color-mix(in srgb, var(--success) 8%, transparent);
    }

    .sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }

    /* Confetti */
    .confetti-overlay {
        position: fixed;
        inset: 0;
        pointer-events: none;
        overflow: hidden;
        z-index: 9999;
    }
    .confetti-piece {
        position: absolute;
        top: -12px;
        left: var(--x, 50%);
        width: 8px;
        height: 12px;
        border-radius: 2px;
        background: hsl(var(--hue, 200deg), 85%, 55%);
        animation: confetti-fall 2.5s var(--delay, 0s) ease-in both;
        transform-origin: center center;
    }
    @keyframes confetti-fall {
        0%   { transform: translateY(0) rotate(0deg) scale(1); opacity: 1; }
        80%  { opacity: 1; }
        100% { transform: translateY(100vh) rotate(720deg) scale(0.5); opacity: 0; }
    }
</style>
