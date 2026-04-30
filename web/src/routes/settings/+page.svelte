<script lang="ts">
    import { onMount } from 'svelte';
    import { api } from '$lib/api';
    import { me, refreshMe } from '$lib/session';
    import { theme, type ThemeMode } from '$lib/theme';

    interface Token {
        id: string;
        name: string;
        token: string | null;
        last_used_at: string | null;
        expires_at: string | null;
        created_at: string;
    }

    interface DueAlert {
        id: string;
        kind: string;
        severity: string;
        title: string;
        collection_id: string;
        item_id: string | null;
        lot_id: string | null;
        due_at: string;
        details: string | null;
    }

    let tokens = $state<Token[]>([]);
    let alerts = $state<DueAlert[]>([]);
    let newName = $state('');
    let issuedRaw = $state('');
    let error = $state('');
    let revokeModalTokenId = $state<string | null>(null);
    let scrubModalOpen = $state(false);
    let scrubConfirmText = $state('');
    let scrubResult = $state('');
    const scrubPhrase = 'SCRUB INVENTORY';

    async function load() {
        try {
            tokens = await api.get<Token[]>('/auth/tokens');
            alerts = await api.get<DueAlert[]>('/alerts?within_days=14');
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function create(e: Event) {
        e.preventDefault();
        if (!newName.trim()) return;
        try {
            const params = new URLSearchParams({ name: newName.trim() });
            const t = await api.post<Token>(`/auth/tokens?${params.toString()}`, undefined);
            issuedRaw = t.token ?? '';
            newName = '';
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function revokeConfirmed() {
        if (!revokeModalTokenId) return;
        await api.delete(`/auth/tokens/${revokeModalTokenId}`);
        revokeModalTokenId = null;
        await load();
    }

    async function scrubInventory() {
        if (scrubConfirmText.trim().toUpperCase() !== scrubPhrase) return;
        try {
            const res = await api.post<{ scrubbed: boolean; deleted_counts: Record<string, number> }>(
                '/admin/system/scrub-inventory',
                { confirmation: scrubConfirmText }
            );
            const total = Object.values(res.deleted_counts).reduce((sum, n) => sum + n, 0);
            scrubResult = `Inventory scrub complete. Deleted ${total} rows.`;
            scrubModalOpen = false;
            scrubConfirmText = '';
            await load();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    onMount(async () => {
        await refreshMe();
        await load();
    });
</script>

<h1>Settings</h1>

{#if error}<p class="error">{error}</p>{/if}
{#if scrubResult}<p class="ok">{scrubResult}</p>{/if}

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">Upcoming alerts</h3>
    <p class="muted">Use-by dates, expirations, and maintenance due in the next 14 days.</p>
    {#if alerts.length === 0}
        <p class="muted">No upcoming alerts.</p>
    {:else}
        <ul class="alerts">
            {#each alerts as a (a.id)}
                <li class={`alert ${a.severity}`}>
                    <strong>{a.title}</strong>
                    <span>{new Date(a.due_at).toLocaleString()}</span>
                    {#if a.details}<span class="muted">{a.details}</span>{/if}
                </li>
            {/each}
        </ul>
    {/if}
</div>

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">Appearance</h3>
    <p class="muted">Choose how Covet looks. "System" follows your OS setting.</p>
    <div role="radiogroup" aria-label="Theme" class="theme-toggle">
        {#each ['light', 'dark', 'system'] as const as opt (opt)}
            <button
                type="button"
                class={$theme === opt ? '' : 'secondary'}
                aria-pressed={$theme === opt}
                onclick={() => theme.set(opt as ThemeMode)}
            >
                {opt[0].toUpperCase() + opt.slice(1)}
            </button>
        {/each}
    </div>
</div>

<div class="card">
    <h3 style="margin-top:0">API tokens</h3>
    <p class="muted">For mobile apps and CLI integrations.</p>

    <form onsubmit={create} style="display:flex; gap:.5rem; margin-bottom:1rem">
        <input bind:value={newName} placeholder="Token name (e.g. Pixel 9)" />
        <button type="submit">Create</button>
    </form>

    {#if issuedRaw}
        <div class="card" style="background: var(--surface-2); margin-bottom: 1rem">
            <p>
                <strong>Save this token now — it won't be shown again:</strong>
            </p>
            <pre style="word-break: break-all; white-space: pre-wrap">{issuedRaw}</pre>
            <button class="secondary" onclick={() => (issuedRaw = '')}>Dismiss</button>
        </div>
    {/if}

    {#if tokens.length === 0}
        <p class="muted">No tokens yet.</p>
    {:else}
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Last used</th>
                    <th>Expires</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {#each tokens as t (t.id)}
                    <tr>
                        <td>{t.name}</td>
                        <td>{t.last_used_at ?? '—'}</td>
                        <td>{t.expires_at ?? 'never'}</td>
                        <td>
                            <button class="danger" onclick={() => (revokeModalTokenId = t.id)}>Revoke</button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
</div>

{#if $me?.is_admin}
    <div class="card" style="margin-top: 1rem">
        <h3 style="margin-top:0">System Maintenance</h3>
        <p class="muted">
            Admin only. Scrub all inventory-domain data for clean rebuilds while developing.
        </p>
        <button class="danger" type="button" onclick={() => (scrubModalOpen = true)}>Scrub Inventory Data</button>
    </div>
{/if}

{#if revokeModalTokenId}
    <div class="modal-backdrop" role="presentation" onclick={() => (revokeModalTokenId = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="revoke-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="revoke-title">Revoke token?</h3>
            <p class="muted">This token will stop working immediately.</p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (revokeModalTokenId = null)}>Cancel</button>
                <button type="button" class="danger" onclick={revokeConfirmed}>Revoke</button>
            </div>
        </div>
    </div>
{/if}

{#if scrubModalOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (scrubModalOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="scrub-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="scrub-title">Scrub inventory data?</h3>
            <p class="muted">
                This deletes collections, items, lots, photos, tags, loans, maintenance, invites, and related sync data.
                Users/accounts are kept.
            </p>
            <label for="scrub-confirm" class="muted">Type {scrubPhrase} to confirm</label>
            <input id="scrub-confirm" bind:value={scrubConfirmText} placeholder={scrubPhrase} />
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (scrubModalOpen = false)}>Cancel</button>
                <button
                    type="button"
                    class="danger"
                    disabled={scrubConfirmText.trim().toUpperCase() !== scrubPhrase}
                    onclick={scrubInventory}
                >Scrub now</button>
            </div>
        </div>
    </div>
{/if}

<style>
    .theme-toggle {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .alerts {
        list-style: none;
        padding: 0;
        margin: 0;
        display: grid;
        gap: 0.5rem;
    }

    .alert {
        display: grid;
        gap: 0.2rem;
        padding: 0.65rem 0.75rem;
        border-radius: 8px;
        border: 1px solid var(--border);
        background: var(--surface-2);
    }

    .alert.warning {
        border-color: #f59e0b;
    }

    .alert.critical {
        border-color: #ef4444;
    }

    .ok {
        color: #16a34a;
    }

    .modal-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.45);
        display: grid;
        place-items: center;
        padding: 1rem;
        z-index: 40;
    }

    .modal {
        width: min(34rem, 100%);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        display: grid;
        gap: 0.75rem;
    }

    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 0.5rem;
    }
</style>
