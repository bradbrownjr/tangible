<script lang="ts">
    import { onMount } from 'svelte';
    import { api } from '$lib/api';
    import { theme, type ThemeMode } from '$lib/theme';

    interface Token {
        id: string;
        name: string;
        token: string | null;
        last_used_at: string | null;
        expires_at: string | null;
        created_at: string;
    }

    let tokens = $state<Token[]>([]);
    let newName = $state('');
    let issuedRaw = $state('');
    let error = $state('');

    async function load() {
        try {
            tokens = await api.get<Token[]>('/auth/tokens');
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

    async function revoke(id: string) {
        if (!confirm('Revoke this token?')) return;
        await api.delete(`/auth/tokens/${id}`);
        await load();
    }

    onMount(load);
</script>

<h1>Settings</h1>

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

    {#if error}<p class="error">{error}</p>{/if}

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
                            <button class="danger" onclick={() => revoke(t.id)}>Revoke</button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
</div>

<style>
    .theme-toggle {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
</style>
