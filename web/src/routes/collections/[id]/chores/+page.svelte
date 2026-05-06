<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Chore, type Collection } from '$lib/api';
    import { ConfirmDialog, Modal } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    let collection = $state<Collection | null>(null);
    let chores = $state<Chore[]>([]);
    let loading = $state(true);
    let error = $state('');

    let newName = $state('');
    let newNotes = $state('');
    let newIntervalDays = $state('');
    let newNextDueAt = $state('');

    let editingId = $state<string | null>(null);
    let editName = $state('');
    let editNotes = $state('');
    let editIntervalDays = $state('');
    let editNextDueAt = $state('');

    let confirmDeleteId = $state<string | null>(null);
    let confirmDeleteLabel = $state('');
    let confirmDeleting = $state(false);

    let completeChoreId = $state<string | null>(null);
    let completeNotes = $state('');
    let completeCost = $state('');
    let completeCurrency = $state('USD');
    let completeTechnician = $state('');
    let completeBusy = $state(false);

    const cid = $derived(page.params.id ?? '');
    const canEdit = $derived(
        collection?.my_role === 'editor' || collection?.my_role === 'owner'
    );

    async function load() {
        loading = true;
        error = '';
        try {
            const [c, ch] = await Promise.all([
                api.get<Collection>(`/collections/${cid}`),
                api.get<Chore[]>(`/collections/${cid}/chores`)
            ]);
            collection = c;
            chores = ch;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    onMount(load);

    async function createChore(e: Event) {
        e.preventDefault();
        if (!newName.trim()) return;
        try {
            await api.post(`/collections/${cid}/chores`, {
                name: newName.trim(),
                notes: newNotes.trim() || null,
                interval_days: newIntervalDays ? parseInt(newIntervalDays) : null,
                next_due_at: newNextDueAt || null
            });
            newName = '';
            newNotes = '';
            newIntervalDays = '';
            newNextDueAt = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function startEdit(ch: Chore) {
        editingId = ch.id;
        editName = ch.name;
        editNotes = ch.notes ?? '';
        editIntervalDays = ch.interval_days ? String(ch.interval_days) : '';
        editNextDueAt = ch.next_due_at ? ch.next_due_at.slice(0, 10) : '';
    }

    async function saveEdit(id: string) {
        try {
            await api.patch(`/chores/${id}`, {
                name: editName.trim(),
                notes: editNotes.trim() || null,
                interval_days: editIntervalDays ? parseInt(editIntervalDays) : null,
                next_due_at: editNextDueAt || null
            });
            editingId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function confirmDelete(id: string, name: string) {
        confirmDeleteId = id;
        confirmDeleteLabel = name;
    }

    async function doDelete() {
        if (!confirmDeleteId) return;
        confirmDeleting = true;
        try {
            await api.delete(`/chores/${confirmDeleteId}`);
            confirmDeleteId = null;
            confirmDeleteLabel = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            confirmDeleting = false;
        }
    }

    function openComplete(id: string) {
        completeChoreId = id;
        completeNotes = '';
        completeCost = '';
        completeCurrency = 'USD';
        completeTechnician = '';
    }

    async function doComplete() {
        if (!completeChoreId) return;
        completeBusy = true;
        try {
            await api.post(`/chores/${completeChoreId}/complete`, {
                notes: completeNotes.trim() || null,
                cost: completeCost ? completeCost : null,
                currency: completeCurrency || null,
                technician: completeTechnician.trim() || null
            });
            completeChoreId = null;
            await load();
        } catch (err) {
            error = (err as Error).message;
        } finally {
            completeBusy = false;
        }
    }

    async function snooze(id: string) {
        const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
        try {
            await api.patch(`/chores/${id}`, { next_due_at: tomorrow });
            await load();
        } catch (err) {
            error = (err as Error).message;
        }
    }

    function daysUntil(isoDate: string | null): string {
        if (!isoDate) return '';
        const diff = Math.round((new Date(isoDate).getTime() - Date.now()) / 86400000);
        if (diff < 0) return $_('maintenance.days_overdue', { values: { days: Math.abs(diff) } });
        if (diff === 0) return $_('maintenance.due_today');
        return $_('maintenance.in_days', { values: { days: diff } });
    }

    function isOverdue(isoDate: string | null): boolean {
        if (!isoDate) return false;
        return new Date(isoDate).getTime() < Date.now();
    }
</script>

<svelte:head><title>{collection?.name ?? 'Collection'} — Chores</title></svelte:head>

{#if loading}
    <p class="loading">{$_('common.loading')}</p>
{:else if error}
    <p class="error">{error}</p>
{:else}
    <div class="page-header">
        <p class="muted">{$_('chores.page_description')}</p>
    </div>

    {#if canEdit}
        <form class="card create-form" onsubmit={createChore}>
            <h2>{$_('chores.add_heading')}</h2>
            <div class="field-row">
                <label>
                    {$_('chores.name_label')}
                    <input bind:value={newName} placeholder={$_('chores.name_placeholder')} required />
                </label>
                <label>
                    {$_('chores.interval_label')}
                    <input type="number" bind:value={newIntervalDays} min="1" max="36500" placeholder={$_('chores.interval_placeholder')} />
                </label>
                <label>
                    {$_('chores.next_due_label')}
                    <input type="date" bind:value={newNextDueAt} />
                </label>
            </div>
            <label>
                {$_('chores.notes_label')}
                <textarea bind:value={newNotes} rows="2" placeholder={$_('chores.notes_placeholder')}></textarea>
            </label>
            <button type="submit">{$_('chores.add_button')}</button>
        </form>
    {/if}

    {#if chores.length === 0}
        <p class="empty">{$_('chores.no_chores')}</p>
    {:else}
        <ul class="chore-list">
            {#each chores as ch (ch.id)}
                <li class="chore-card" class:overdue={isOverdue(ch.next_due_at)}>
                    {#if isOverdue(ch.next_due_at)}
                        <Icon name="circle-alert" size={16} class="overdue-icon" />
                    {/if}
                    {#if editingId === ch.id}
                        <form class="edit-inline" onsubmit={(e) => { e.preventDefault(); saveEdit(ch.id); }}>
                            <input bind:value={editName} required />
                            <input type="number" bind:value={editIntervalDays} min="1" placeholder="Interval (days)" />
                            <input type="date" bind:value={editNextDueAt} />
                            <textarea bind:value={editNotes} rows="2" placeholder={$_('chores.notes_placeholder')}></textarea>
                            <div class="btn-row">
                                <button type="submit">{$_('chores.save_button')}</button>
                                <button type="button" class="secondary" onclick={() => (editingId = null)}>{$_('common.cancel')}</button>
                            </div>
                        </form>
                    {:else}
                        <div class="chore-main">
                            <span class="chore-name">{ch.name}</span>
                            {#if ch.next_due_at}
                                <span class="due-badge" class:overdue={isOverdue(ch.next_due_at)}>
                                    {daysUntil(ch.next_due_at)}
                                </span>
                            {/if}
                            {#if ch.interval_days}
                                <span class="interval">{$_('chores.interval_display', {values: {days: ch.interval_days}})}</span>
                            {/if}
                        </div>
                        {#if ch.notes}
                            <p class="chore-notes">{ch.notes}</p>
                        {/if}
                        {#if ch.last_completed_at}
                            <p class="last-done">
                                {$_('chores.last_done_label')} <time datetime={ch.last_completed_at}>{new Date(ch.last_completed_at).toLocaleDateString()}</time>
                            </p>
                        {/if}
                        {#if canEdit}
                            <div class="btn-row">
                                <button class="success" onclick={() => openComplete(ch.id)}>{$_('chores.mark_done_button')}</button>
                                {#if isOverdue(ch.next_due_at)}
                                    <button class="secondary" onclick={() => snooze(ch.id)}>{$_('chores.snooze_button')}</button>
                                {/if}
                                <button class="secondary" onclick={() => startEdit(ch)}>{$_('chores.edit_button')}</button>
                                <button class="danger" onclick={() => confirmDelete(ch.id, ch.name)}>{$_('chores.delete_button')}</button>
                            </div>
                        {/if}
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
{/if}

<!-- Mark done modal -->
<Modal open={!!completeChoreId} title={$_('chores.mark_done_title')} onclose={() => (completeChoreId = null)}>
    {#snippet footer()}
        <button class="success" onclick={doComplete} disabled={completeBusy}>{$_('chores.mark_done_save')}</button>
        <button class="secondary" onclick={() => (completeChoreId = null)}>{$_('common.cancel')}</button>
    {/snippet}
    <label>
        {$_('chores.mark_done_notes_label')}
        <textarea bind:value={completeNotes} rows="2" placeholder={$_('chores.mark_done_notes_placeholder')}></textarea>
    </label>
    <div class="field-row">
        <label>
            {$_('chores.mark_done_cost_label')}
            <input type="number" step="0.01" bind:value={completeCost} placeholder={$_('chores.mark_done_cost_placeholder')} />
        </label>
        <label>
            {$_('chores.mark_done_currency_label')}
            <input bind:value={completeCurrency} maxlength="3" placeholder={$_('chores.mark_done_currency_placeholder')} />
        </label>
    </div>
    <label>
        {$_('chores.mark_done_tech_label')}
        <input bind:value={completeTechnician} placeholder={$_('chores.mark_done_tech_placeholder')} />
    </label>
</Modal>

<ConfirmDialog
    open={!!confirmDeleteId}
    confirmLabel={$_('chores.delete_confirm')}
    variant="danger"
    loading={confirmDeleting}
    onconfirm={doDelete}
    oncancel={() => { confirmDeleteId = null; confirmDeleteLabel = ''; }}
>
    {$_('chores.delete_text', {values: {name: confirmDeleteLabel}})}
</ConfirmDialog>

<style>
    .page-header { margin-bottom: 1.5rem; }
    .create-form { padding: 1rem; margin-bottom: 1.5rem; }
    .field-row { display: flex; gap: 1rem; flex-wrap: wrap; }
    .field-row label { flex: 1; min-width: 160px; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
    .chore-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.75rem; }
    .chore-card {
        padding: 1rem;
        border: 1px solid var(--border);
        border-left: 4px solid transparent;
        border-radius: var(--radius-md);
        background: var(--surface);
        position: relative;
    }
    .chore-card.overdue { border-left-color: var(--danger); background: color-mix(in srgb, var(--danger) 5%, var(--surface)); }
    :global(.overdue-icon) { position: absolute; top: 0.75rem; right: 0.75rem; color: var(--danger); }
    .chore-main { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .chore-name { font-weight: 600; }
    .due-badge { font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: var(--radius-full); background: color-mix(in srgb, var(--warning) 15%, transparent); color: var(--warning); }
    .due-badge.overdue { background: color-mix(in srgb, var(--danger) 15%, transparent); color: var(--danger); }
    .interval { font-size: 0.8rem; color: var(--text-muted); }
    .chore-notes { margin: 0.5rem 0 0; font-size: 0.875rem; color: var(--text-muted); }
    .last-done { margin: 0.25rem 0 0; font-size: 0.8rem; color: var(--text-muted); }
    .btn-row { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
    .edit-inline { display: flex; flex-direction: column; gap: 0.5rem; }
    .loading, .empty { text-align: center; color: var(--text-muted); padding: 2rem; }
    .success { background: var(--success); color: #fff; border: none; }
    .success:hover { filter: brightness(1.1); }
</style>
