<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { api, ApiError, type DueAlert, type Chore, type StandaloneTask, type Collection, type ScoreboardEntry } from '$lib/api';
    import { _ } from 'svelte-i18n';
    import { EmptyState } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    let alerts = $state<DueAlert[]>([]);
    let loading = $state(true);
    let error = $state('');
    let withinDays = $state(30);
    let tab = $state<'chores' | 'my-tasks' | 'scoreboard'>('chores');
    let showConfetti = $state(false);

    // ── My Tasks tab state ──
    let myTasks = $state<StandaloneTask[]>([]);
    let taskCollections = $state<Collection[]>([]);
    let tasksLoading = $state(false);
    let tasksError = $state('');
    let showNewTaskForm = $state(false);
    let newTitle = $state('');
    let newNotes = $state('');
    let newDueAt = $state('');
    let newCollectionId = $state('');

    function taskErrMsg(e: unknown): string {
        if (e instanceof ApiError && e.status === 429) return 'Too many requests — please wait a moment and try again.';
        return (e as Error).message;
    }
    let taskSaving = $state(false);
    let tasksFetched = false;

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

    onMount(() => {
        load();
    });

    $effect(() => {
        const tabParam = page.url.searchParams.get('tab');
        if (tabParam === 'chores' || tabParam === 'my-tasks' || tabParam === 'scoreboard') {
            tab = tabParam;
        }
    });

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

    // Chores tab: only chore_due alerts, sorted by due_at
    const choreAlerts = $derived(
        sorted.filter(a => a.kind === 'chore_due')
    );

    function launchConfetti() {
        showConfetti = true;
        setTimeout(() => { showConfetti = false; }, 2500);
    }

    async function loadTasks() {
        if (tasksLoading) return;
        tasksLoading = true;
        tasksError = '';
        try {
            const [tasks, cols] = await Promise.all([
                api.get<StandaloneTask[]>('/tasks'),
                taskCollections.length
                    ? Promise.resolve(taskCollections)
                    : api.get<Collection[]>('/collections'),
            ]);
            myTasks = tasks;
            taskCollections = cols;
            if (!newCollectionId && cols.length) newCollectionId = cols[0].id;
        } catch (e) {
            tasksError = taskErrMsg(e);
        } finally {
            tasksLoading = false;
        }
    }

    $effect(() => {
        if (tab === 'my-tasks' && !tasksFetched) {
            tasksFetched = true;
            loadTasks();
        }
    });

    async function createTask() {
        if (!newTitle.trim() || !newCollectionId) return;
        taskSaving = true;
        tasksError = '';
        try {
            const t = await api.post<StandaloneTask>(`/collections/${newCollectionId}/tasks`, {
                title: newTitle.trim(),
                notes: newNotes.trim() || null,
                due_at: newDueAt || null,
            });
            myTasks = [...myTasks, t];
            newTitle = '';
            newNotes = '';
            newDueAt = '';
            showNewTaskForm = false;
        } catch (e) {
            tasksError = taskErrMsg(e);
        } finally {
            taskSaving = false;
        }
    }

    async function completeTask(id: string) {
        try {
            await api.post(`/tasks/${id}/complete`, {});
            myTasks = myTasks.filter(t => t.id !== id);
            launchConfetti();
        } catch (e) {
            tasksError = taskErrMsg(e);
        }
    }

    async function deleteTask(id: string) {
        try {
            await api.delete(`/tasks/${id}`);
            myTasks = myTasks.filter(t => t.id !== id);
        } catch (e) {
            tasksError = taskErrMsg(e);
        }
    }

    // ── Scoreboard tab state ──
    let scoreboard = $state<ScoreboardEntry[]>([]);
    let scoreboardLoading = $state(false);
    let scoreboardError = $state('');
    let scoreboardLoaded = $state(false);
    let scoreboardFetched = false;

    const ACHIEVEMENT_EMOJI: Record<string, string> = {
        first_finish:   '🏅',
        getting_started:'⭐',
        on_a_roll:      '🔥',
        power_user:     '💪',
        household_hero: '🏆',
        legend:         '👑',
    };

    async function loadScoreboard() {
        if (scoreboardLoading) return;
        scoreboardLoading = true;
        scoreboardError = '';
        try {
            scoreboard = await api.get<ScoreboardEntry[]>('/tasks/scoreboard');
            scoreboardLoaded = true;
        } catch (e) {
            scoreboardError = (e as Error).message;
        } finally {
            scoreboardLoading = false;
        }
    }

    $effect(() => {
        if (tab === 'scoreboard' && !scoreboardFetched) {
            scoreboardFetched = true;
            loadScoreboard();
        }
    });

    // ── New Chore form state ──
    let choreCollectionsFetched = false;
    let choreCollections = $state<Collection[]>([]);
    let choreCollectionsLoading = $state(false);
    let showNewChoreForm = $state(false);
    let newChoreName = $state('');
    let newChoreCollectionId = $state('');
    let newChoreIntervalDays = $state('');
    let newChoreNotes = $state('');
    let choreSaving = $state(false);
    let choreFormError = $state('');

    // ── Standalone chores state ──
    let chores = $state<Chore[]>([]);
    let choresLoaded = false;

    $effect(() => {
        if (tab === 'chores') {
            if (!choreCollectionsFetched) {
                choreCollectionsFetched = true;
                choreCollectionsLoading = true;
                api.get<Collection[]>('/collections')
                    .then(cols => {
                        choreCollections = cols;
                        // don't auto-select; let the user choose (or leave blank for standalone)
                    })
                    .catch(() => {})
                    .finally(() => { choreCollectionsLoading = false; });
            }
            if (!choresLoaded) {
                choresLoaded = true;
                api.get<Chore[]>('/chores').then(c => { chores = c; }).catch(() => {});
            }
        }
    });

    async function completeChore(id: string) {
        try {
            await api.post(`/chores/${id}/complete`, {});
            chores = await api.get<Chore[]>('/chores');
            launchConfetti();
        } catch (e) {
            // silently ignore
        }
    }

    function isChoreCompletable(chore: Chore): boolean {
        if (chore.interval_days === null) return chore.last_completed_at === null;
        if (!chore.next_due_at) return true;
        return new Date(chore.next_due_at) <= new Date();
    }

    async function createChore() {
        if (!newChoreName.trim()) return;
        choreSaving = true;
        choreFormError = '';
        try {
            const body = {
                name: newChoreName.trim(),
                interval_days: newChoreIntervalDays ? parseInt(newChoreIntervalDays, 10) : null,
                notes: newChoreNotes.trim() || null,
            };
            if (newChoreCollectionId) {
                await api.post(`/collections/${newChoreCollectionId}/chores`, body);
            } else {
                await api.post('/chores', body);
            }
            newChoreName = '';
            newChoreIntervalDays = '';
            newChoreNotes = '';
            showNewChoreForm = false;
            await load();
            chores = await api.get<Chore[]>('/chores');
        } catch (e) {
            choreFormError = (e as Error).message;
        } finally {
            choreSaving = false;
        }
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
        aria-selected={tab === 'chores'}
        class="tab-btn"
        class:active={tab === 'chores'}
        onclick={() => (tab = 'chores')}
    >
        <Icon name="sparkles" size={15} />
        {$_('tasks.tab_chores')}
        {#if choreAlerts.length + chores.length > 0}
            <span class="tab-badge">{choreAlerts.length + chores.length}</span>
        {/if}
    </button>
    <button
        role="tab"
        aria-selected={tab === 'my-tasks'}
        class="tab-btn"
        class:active={tab === 'my-tasks'}
        onclick={() => (tab = 'my-tasks')}
    >
        <Icon name="check-circle" size={15} />
        {$_('tasks.tab_my_tasks')}
        {#if myTasks.length > 0}
            <span class="tab-badge">{myTasks.length}</span>
        {/if}
    </button>
    <button
        role="tab"
        aria-selected={tab === 'scoreboard'}
        class="tab-btn"
        class:active={tab === 'scoreboard'}
        onclick={() => (tab = 'scoreboard')}
    >
        <Icon name="users" size={15} />
        {$_('tasks.tab_scoreboard')}
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
{:else if tab === 'chores'}
    <!-- ── Chores tab ── -->
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
                        {#if alert.collection_id}
                        <a href="/collections/{alert.collection_id}/chores">
                            <Icon name="sparkles" size={12} />
                            {$_('tasks.manage_chores_link')}
                        </a>
                        <a href="/collections/{alert.collection_id}">{$_('maintenance.collection_link')}</a>
                        {/if}
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
        {#each chores as chore (chore.id)}
            {@const completable = isChoreCompletable(chore)}
            <li class="alert-card chore-card" class:chore-not-due={!completable}>
                <div class="alert-left">
                    <Icon name="sparkles" size={16} class="sev-icon" />
                </div>
                <div class="alert-body">
                    <div class="alert-main">
                        <span class="alert-title">{chore.name}</span>
                        {#if chore.next_due_at}
                            <span class="due-badge">
                                <time datetime={chore.next_due_at}>{daysLabel(chore.next_due_at)}</time>
                            </span>
                        {/if}
                    </div>
                    {#if chore.notes}
                        <p class="alert-detail">{chore.notes}</p>
                    {/if}
                </div>
                <div class="chore-actions">
                    <button
                        class="done-btn"
                        title={completable ? $_('tasks.mark_done_tooltip') : $_('tasks.chore_not_due_tooltip')}
                        disabled={!completable}
                        onclick={() => completeChore(chore.id)}
                    >
                        <Icon name="calendar-check" size={16} />
                        <span class="sr-only">{$_('tasks.mark_done_tooltip')}</span>
                    </button>
                </div>
            </li>
        {/each}
        {#if showNewChoreForm}
            <li class="new-form-li">
                <form class="new-task-form" onsubmit={(e) => { e.preventDefault(); createChore(); }}>
                    {#if choreFormError}
                        <p class="error">{choreFormError}</p>
                    {/if}
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-group-label" for="chore-name">{$_('chores.name_label')}</label>
                            <input
                                id="chore-name"
                                type="text"
                                class="form-input"
                                placeholder={$_('chores.name_placeholder')}
                                bind:value={newChoreName}
                                required
                            />
                        </div>
                        <div class="form-group">
                            <label class="form-group-label" for="chore-collection">{$_('chores.collection_label')}</label>
                            <select id="chore-collection" bind:value={newChoreCollectionId} class="form-select">
                                <option value="" disabled>{$_('chores.collection_none')}</option>
                                {#each choreCollections as col (col.id)}
                                    <option value={col.id}>{col.name}</option>
                                {/each}
                            </select>
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label class="form-group-label" for="chore-interval">{$_('chores.interval_label')}</label>
                            <input
                                id="chore-interval"
                                type="number"
                                class="form-input"
                                placeholder={$_('chores.interval_placeholder')}
                                bind:value={newChoreIntervalDays}
                                min="1"
                                max="36500"
                            />
                        </div>
                        <div class="form-group">
                            <label class="form-group-label" for="chore-notes">{$_('chores.notes_label')}</label>
                            <input
                                id="chore-notes"
                                type="text"
                                class="form-input"
                                placeholder={$_('chores.notes_placeholder')}
                                bind:value={newChoreNotes}
                            />
                        </div>
                    </div>
                    <div class="form-actions">
                        <button
                            type="submit"
                            class="btn-primary"
                            disabled={choreSaving || !newChoreName.trim()}
                        >
                            {#if choreSaving}
                                <Icon name="loader" size={14} />
                            {:else}
                                <Icon name="sparkles" size={14} />
                            {/if}
                            {$_('chores.add_button')}
                        </button>
                        <button type="button" class="btn-ghost" onclick={() => { showNewChoreForm = false; choreFormError = ''; }}>
                            {$_('tasks.new_task_cancel')}
                        </button>
                    </div>
                </form>
            </li>
        {:else}
            <li>
                <button class="new-card-li" onclick={() => { showNewChoreForm = true; }}>
                    <Icon name="plus" size={16} />
                    {$_('tasks.new_chore_button')}
                </button>
            </li>
        {/if}
    </ul>
{:else if tab === 'my-tasks'}
    <!-- ── My Tasks tab ── -->
    {#if tasksError}
        <p class="error">{tasksError}</p>
    {/if}
    <p class="tab-hint">{$_('tasks.my_tasks_hint')}</p>

    {#if tasksLoading}
        <EmptyState icon="loader" heading={$_('common.loading')} />
    {:else}
        <ul class="alert-list">
            {#each myTasks as task (task.id)}
                {@const overdue = !!task.due_at && new Date(task.due_at) < new Date()}
                {@const hasDue = !!task.due_at}
                <li
                    class="alert-card task-card"
                    class:severity-critical={overdue}
                    class:severity-warning={hasDue && !overdue}
                >
                    <div class="alert-left">
                        <Icon
                            name="check-circle"
                            size={16}
                            class="sev-icon {overdue ? 'sev-critical' : hasDue ? 'sev-warning' : ''}"
                        />
                    </div>
                    <div class="alert-body">
                        <div class="alert-main">
                            <span class="alert-title">{task.title}</span>
                            {#if task.due_at}
                                <span class="due-badge" class:critical={overdue}>
                                    <time datetime={task.due_at}>{daysLabel(task.due_at)}</time>
                                </span>
                            {/if}
                        </div>
                        {#if task.notes}
                            <p class="alert-detail">{task.notes}</p>
                        {/if}
                        <div class="alert-links">
                            {#if task.item_id}
                                <a href="/collections/{task.collection_id}?item={task.item_id}">
                                    {$_('maintenance.view_item_link')}
                                </a>
                            {/if}
                            <a href="/collections/{task.collection_id}">{$_('maintenance.collection_link')}</a>
                        </div>
                    </div>
                    <div class="chore-actions">
                        <button
                            class="done-btn"
                            title={$_('tasks.complete_tooltip')}
                            onclick={() => completeTask(task.id)}
                        >
                            <Icon name="check-circle" size={16} />
                            <span class="sr-only">{$_('tasks.complete_tooltip')}</span>
                        </button>
                        <button
                            class="done-btn delete-btn"
                            title={$_('tasks.delete_tooltip')}
                            onclick={() => deleteTask(task.id)}
                        >
                            <Icon name="trash-2" size={16} />
                            <span class="sr-only">{$_('tasks.delete_tooltip')}</span>
                        </button>
                    </div>
                </li>
            {/each}
            {#if showNewTaskForm}
                <li class="new-form-li">
                    <form class="new-task-form" onsubmit={(e) => { e.preventDefault(); createTask(); }}>
                        <div class="form-row">
                            <input
                                type="text"
                                class="form-input"
                                placeholder={$_('tasks.new_task_title_placeholder')}
                                bind:value={newTitle}
                                required
                            />
                            <select bind:value={newCollectionId} class="form-select">
                                {#each taskCollections as col (col.id)}
                                    <option value={col.id}>{col.name}</option>
                                {/each}
                            </select>
                        </div>
                        <div class="form-row">
                            <input
                                type="text"
                                class="form-input"
                                placeholder={$_('tasks.new_task_notes_placeholder')}
                                bind:value={newNotes}
                            />
                            <label class="due-label">
                                <span>{$_('tasks.new_task_due_label')}</span>
                                <input type="datetime-local" class="form-input" bind:value={newDueAt} />
                            </label>
                        </div>
                        <div class="form-actions">
                            <button type="submit" class="btn-primary" disabled={taskSaving || !newTitle.trim()}>
                                {#if taskSaving}
                                    <Icon name="loader" size={14} />
                                {:else}
                                    <Icon name="check-circle" size={14} />
                                {/if}
                                {$_('tasks.new_task_save')}
                            </button>
                            <button type="button" class="btn-ghost" onclick={() => { showNewTaskForm = false; }}>
                                {$_('tasks.new_task_cancel')}
                            </button>
                        </div>
                    </form>
                </li>
            {:else}
                <li>
                    <button class="new-card-li" onclick={() => { showNewTaskForm = true; loadTasks(); }}>
                        <Icon name="plus" size={16} />
                        {$_('tasks.new_task_button')}
                    </button>
                </li>
            {/if}
        </ul>
    {/if}
{:else if tab === 'scoreboard'}
    <!-- ── Scoreboard tab ── -->
    {#if scoreboardError}
        <p class="error">{scoreboardError}</p>
    {/if}
    {#if scoreboardLoading}
        <EmptyState icon="loader" heading={$_('common.loading')} />
    {:else if scoreboard.length === 0 && scoreboardLoaded}
        <EmptyState
            icon="users"
            heading={$_('tasks.scoreboard_empty')}
            body={$_('tasks.scoreboard_hint')}
        />
    {:else if !scoreboardLoaded}
        <!-- trigger effect on first render -->
    {:else}
        <p class="tab-hint">{$_('tasks.scoreboard_hint')}</p>
        <ol class="scoreboard-list">
            {#each scoreboard as entry, idx (entry.user_id)}
                <li class="scoreboard-row" class:top-three={idx < 3}>
                    <span class="rank" aria-hidden="true">
                        {idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : `${idx + 1}.`}
                    </span>
                    <div class="scoreboard-member">
                        <span class="member-name">{entry.display_name}</span>
                        <div class="score-breakdown">
                            {#if entry.chore_count > 0}
                                <span class="score-chip">
                                    <Icon name="sparkles" size={11} />
                                    {entry.chore_count}
                                </span>
                            {/if}
                            {#if entry.maintenance_count > 0}
                                <span class="score-chip">
                                    <Icon name="wrench" size={11} />
                                    {entry.maintenance_count}
                                </span>
                            {/if}
                            {#if entry.task_count > 0}
                                <span class="score-chip">
                                    <Icon name="check-circle" size={11} />
                                    {entry.task_count}
                                </span>
                            {/if}
                        </div>
                        {#if entry.achievements.length > 0}
                            <div class="achievements">
                                {#each entry.achievements as badge (badge)}
                                    <span
                                        class="badge"
                                        title={$_(`tasks.achievement_${badge}`)}
                                    >{ACHIEVEMENT_EMOJI[badge] ?? '🎖️'}</span>
                                {/each}
                            </div>
                        {/if}
                    </div>
                    <span class="score-total">{entry.total}</span>
                </li>
            {/each}
        </ol>
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

    .filter-row { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .filter-row button { min-height: unset; }
    label { display: flex; flex-direction: row; align-items: center; gap: 0.5rem; font-size: 0.875rem; }

    .tab-hint { font-size: 0.82rem; color: var(--text-muted); margin-bottom: 0.75rem; }

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
    .done-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
        pointer-events: none;
    }
    .chore-not-due { opacity: 0.55; }

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

    /* New card / inline form at bottom of list */
    .new-card-li {
        width: 100%;
        padding: 0.75rem 1rem;
        border-radius: var(--radius-md);
        border: 2px dashed var(--border);
        background: transparent;
        cursor: pointer;
        color: var(--accent);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-size: 0.875rem;
    }
    .new-card-li:hover {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 8%, transparent);
    }
    .new-form-li {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem;
    }
    .new-form-li .new-task-form { background: none; border: none; border-radius: 0; padding: 0; margin-bottom: 0; }

    .new-task-form {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        padding: 1rem;
        margin-bottom: 1.25rem;
        display: flex;
        flex-direction: column;
        gap: 0.65rem;
    }
    .form-row { display: flex; gap: 0.65rem; flex-wrap: wrap; }
    .form-group { display: flex; flex-direction: column; gap: 0.2rem; flex: 1; min-width: 0; }
    .form-group-label { font-size: 0.75rem; color: var(--text-muted); }
    .form-group .form-input, .form-group .form-select { flex: unset; width: 100%; }
    .form-input, .form-select {
        flex: 1;
        min-width: 0;
        padding: 0.45rem 0.65rem;
        border: 1px solid var(--border);
        border-radius: var(--radius-sm);
        background: var(--surface);
        color: var(--text);
        font-size: 0.875rem;
    }
    .form-input:focus, .form-select:focus { outline: none; border-color: var(--accent); }
    .due-label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.8rem; color: var(--text-muted); flex: 1; min-width: 0; }
    .due-label .form-input { flex: unset; width: 100%; }
    .form-actions { display: flex; gap: 0.5rem; }
    .btn-primary {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        background: var(--accent);
        color: #fff;
        border: none;
        padding: 0.45rem 1rem;
        border-radius: var(--radius-md);
        cursor: pointer;
        font-size: 0.875rem;
        font-weight: 600;
        transition: opacity 0.15s;
    }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary:not(:disabled):hover { opacity: 0.88; }
    .btn-ghost {
        background: none;
        border: 1px solid var(--border);
        color: var(--text-muted);
        padding: 0.45rem 0.85rem;
        border-radius: var(--radius-md);
        cursor: pointer;
        font-size: 0.875rem;
        transition: color 0.15s;
    }
    .btn-ghost:hover { color: var(--text); }

    .delete-btn:hover {
        color: var(--danger) !important;
        border-color: var(--danger) !important;
        background: color-mix(in srgb, var(--danger) 8%, transparent) !important;
    }

    /* Scoreboard */
    .scoreboard-list {
        list-style: none;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        counter-reset: none;
    }
    .scoreboard-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius-md);
        transition: background 0.15s;
    }
    .scoreboard-row.top-three {
        border-color: var(--accent);
        background: color-mix(in srgb, var(--accent) 4%, var(--surface));
    }
    .rank {
        font-size: 1.25rem;
        width: 2rem;
        text-align: center;
        flex-shrink: 0;
    }
    .scoreboard-member {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }
    .member-name {
        font-weight: 600;
        font-size: 0.95rem;
    }
    .score-breakdown {
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
    }
    .score-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.2rem;
        font-size: 0.72rem;
        color: var(--text-muted);
        background: var(--surface-2);
        padding: 0.1rem 0.4rem;
        border-radius: var(--radius-full);
    }
    .achievements {
        display: flex;
        gap: 0.25rem;
        flex-wrap: wrap;
    }
    .badge {
        font-size: 1rem;
        cursor: default;
    }
    .score-total {
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--accent);
        flex-shrink: 0;
        min-width: 2.5rem;
        text-align: right;
    }
</style>
