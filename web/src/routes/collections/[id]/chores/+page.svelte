<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { api, type Chore, type Collection } from '$lib/api';

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

    let completeChoreId = $state<string | null>(null);
    let completeNotes = $state('');
    let completeCost = $state('');
    let completeCurrency = $state('USD');
    let completeTechnician = $state('');

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
        try {
            await api.delete(`/chores/${confirmDeleteId}`);
            confirmDeleteId = null;
            confirmDeleteLabel = '';
            await load();
        } catch (err) {
            error = (err as Error).message;
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
        }
    }

    function daysUntil(isoDate: string | null): string {
        if (!isoDate) return '';
        const diff = Math.round(
            (new Date(isoDate).getTime() - Date.now()) / 86400000
        );
        if (diff < 0) return `${Math.abs(diff)}d overdue`;
        if (diff === 0) return 'due today';
        return `in ${diff}d`;
    }

    function isOverdue(isoDate: string | null): boolean {
        if (!isoDate) return false;
        return new Date(isoDate).getTime() < Date.now();
    }
</script>

<svelte:head><title>{collection?.name ?? 'Collection'} — Chores</title></svelte:head>

{#if loading}
    <p class="loading">Loading…</p>
{:else if error}
    <p class="error">{error}</p>
{:else}
    <nav class="subnav" aria-label="Collection sections">
        <a class="tab" href="/collections/{cid}">Items</a>
        <a class="tab" href="/collections/{cid}/templates">Templates</a>
        <a class="tab" href="/collections/{cid}/locations">Locations</a>
        <a class="tab" href="/collections/{cid}/bundles">Bundles</a>
        <a class="tab tab-active" href="/collections/{cid}/chores" aria-current="page">Chores</a>
        <a class="tab" href="/collections/{cid}/members">Members</a>
    </nav>

    <div class="page-header">
        <h1>{collection?.name} — Chores</h1>
        <p class="hint">Recurring household tasks that aren't tied to a specific item.</p>
    </div>

    {#if canEdit}
        <form class="card create-form" onsubmit={createChore}>
            <h2>Add chore</h2>
            <div class="field-row">
                <label>
                    Name
                    <input bind:value={newName} placeholder="Clean gutters" required />
                </label>
                <label>
                    Repeat every (days)
                    <input
                        type="number"
                        bind:value={newIntervalDays}
                        min="1"
                        max="36500"
                        placeholder="180"
                    />
                </label>
                <label>
                    Next due
                    <input type="date" bind:value={newNextDueAt} />
                </label>
            </div>
            <label>
                Notes
                <textarea bind:value={newNotes} rows="2" placeholder="Optional notes"></textarea>
            </label>
            <button type="submit" class="btn-primary">Add chore</button>
        </form>
    {/if}

    {#if chores.length === 0}
        <p class="empty">No chores yet.</p>
    {:else}
        <ul class="chore-list">
            {#each chores as ch (ch.id)}
                <li class="chore-card" class:overdue={isOverdue(ch.next_due_at)}>
                    {#if editingId === ch.id}
                        <form class="edit-inline" onsubmit={(e) => { e.preventDefault(); saveEdit(ch.id); }}>
                            <input bind:value={editName} required />
                            <input
                                type="number"
                                bind:value={editIntervalDays}
                                min="1"
                                placeholder="Interval (days)"
                            />
                            <input type="date" bind:value={editNextDueAt} />
                            <textarea bind:value={editNotes} rows="2" placeholder="Notes"></textarea>
                            <div class="btn-row">
                                <button type="submit" class="btn-primary">Save</button>
                                <button type="button" onclick={() => (editingId = null)}>Cancel</button>
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
                                <span class="interval">every {ch.interval_days}d</span>
                            {/if}
                        </div>
                        {#if ch.notes}
                            <p class="chore-notes">{ch.notes}</p>
                        {/if}
                        {#if ch.last_completed_at}
                            <p class="last-done">
                                Last done: {new Date(ch.last_completed_at).toLocaleDateString()}
                            </p>
                        {/if}
                        {#if canEdit}
                            <div class="btn-row">
                                <button class="btn-success" onclick={() => openComplete(ch.id)}>
                                    Mark done
                                </button>
                                <button onclick={() => startEdit(ch)}>Edit</button>
                                <button
                                    class="btn-danger"
                                    onclick={() => confirmDelete(ch.id, ch.name)}
                                >
                                    Delete
                                </button>
                            </div>
                        {/if}
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
{/if}

<!-- Mark done modal -->
{#if completeChoreId}
    <div class="modal-backdrop" role="dialog" aria-modal="true">
        <div class="modal">
            <h2>Mark chore done</h2>
            <label>
                Notes
                <textarea bind:value={completeNotes} rows="2" placeholder="What was done?"></textarea>
            </label>
            <div class="field-row">
                <label>
                    Cost
                    <input type="number" step="0.01" bind:value={completeCost} placeholder="0.00" />
                </label>
                <label>
                    Currency
                    <input bind:value={completeCurrency} maxlength="3" placeholder="USD" />
                </label>
            </div>
            <label>
                Technician / who
                <input bind:value={completeTechnician} placeholder="self" />
            </label>
            <div class="btn-row">
                <button class="btn-primary" onclick={doComplete}>Save</button>
                <button onclick={() => (completeChoreId = null)}>Cancel</button>
            </div>
        </div>
    </div>
{/if}

<!-- Confirm delete modal -->
{#if confirmDeleteId}
    <div class="modal-backdrop" role="dialog" aria-modal="true">
        <div class="modal">
            <p>Delete chore <strong>{confirmDeleteLabel}</strong>? This cannot be undone.</p>
            <div class="btn-row">
                <button class="btn-danger" onclick={doDelete}>Delete</button>
                <button onclick={() => { confirmDeleteId = null; confirmDeleteLabel = ''; }}>
                    Cancel
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
    .subnav {
        display: flex;
        gap: 0.5rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--color-border, #ddd);
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }
    .tab { padding: 0.4rem 0.8rem; border-radius: 4px; text-decoration: none; color: inherit; }
    .tab:hover { background: var(--color-hover, #f0f0f0); }
    .tab-active { background: var(--color-primary, #4f46e5); color: #fff; }
    .page-header { margin-bottom: 1.5rem; }
    .hint { color: var(--color-muted, #666); margin-top: 0.25rem; }
    .create-form { padding: 1rem; margin-bottom: 1.5rem; }
    .field-row { display: flex; gap: 1rem; flex-wrap: wrap; }
    .field-row label { flex: 1; min-width: 160px; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.875rem; }
    input, textarea, select { padding: 0.4rem 0.6rem; border: 1px solid var(--color-border, #ddd); border-radius: 4px; font-size: 0.875rem; }
    .card { background: var(--color-surface, #fff); border: 1px solid var(--color-border, #ddd); border-radius: 8px; padding: 1rem; }
    .chore-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 0.75rem; }
    .chore-card { padding: 1rem; border: 1px solid var(--color-border, #ddd); border-radius: 8px; background: var(--color-surface, #fff); }
    .chore-card.overdue { border-color: var(--color-danger, #dc2626); background: color-mix(in srgb, var(--color-danger, #dc2626) 5%, transparent); }
    .chore-main { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .chore-name { font-weight: 600; }
    .due-badge { font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 9999px; background: var(--color-warning-bg, #fef3c7); color: var(--color-warning, #92400e); }
    .due-badge.overdue { background: var(--color-danger-bg, #fee2e2); color: var(--color-danger, #dc2626); }
    .interval { font-size: 0.8rem; color: var(--color-muted, #666); }
    .chore-notes { margin: 0.5rem 0 0; font-size: 0.875rem; color: var(--color-muted, #666); }
    .last-done { margin: 0.25rem 0 0; font-size: 0.8rem; color: var(--color-muted, #666); }
    .btn-row { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }
    button { padding: 0.4rem 0.8rem; border: 1px solid var(--color-border, #ddd); border-radius: 4px; cursor: pointer; font-size: 0.875rem; background: var(--color-surface, #fff); }
    .btn-primary { background: var(--color-primary, #4f46e5); color: #fff; border-color: transparent; }
    .btn-danger { background: var(--color-danger, #dc2626); color: #fff; border-color: transparent; }
    .btn-success { background: var(--color-success, #16a34a); color: #fff; border-color: transparent; }
    .edit-inline { display: flex; flex-direction: column; gap: 0.5rem; }
    .modal-backdrop { position: fixed; inset: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 1000; }
    .modal { background: var(--color-surface, #fff); border-radius: 8px; padding: 1.5rem; max-width: 480px; width: 100%; display: flex; flex-direction: column; gap: 1rem; }
    .loading, .empty { text-align: center; color: var(--color-muted, #666); padding: 2rem; }
    .error { color: var(--color-danger, #dc2626); padding: 1rem; }
</style>
