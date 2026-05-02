<script lang="ts">
    import { goto } from '$app/navigation';
    import { api } from '$lib/api';
    import { publicConfig, refreshMe } from '$lib/session';

    let username = $state('');
    let password = $state('');
    let totpCode = $state('');
    let totpTicket = $state<string | null>(null);
    let error = $state('');
    let busy = $state(false);

    async function submit(e: Event) {
        e.preventDefault();
        busy = true;
        error = '';
        try {
            const res = await api.post<{ totp_required?: boolean; ticket?: string }>('/auth/login', { username, password });
            if (res.totp_required && res.ticket) {
                totpTicket = res.ticket;
            } else {
                await refreshMe();
                await goto('/');
            }
        } catch (e) {
            error = (e as Error).message;
        } finally {
            busy = false;
        }
    }

    async function submitTotp(e: Event) {
        e.preventDefault();
        busy = true;
        error = '';
        try {
            await api.post('/auth/totp/confirm-login', { ticket: totpTicket, code: totpCode });
            await refreshMe();
            await goto('/');
        } catch (e) {
            error = (e as Error).message;
        } finally {
            busy = false;
        }
    }

    function backToLogin() {
        totpTicket = null;
        totpCode = '';
        error = '';
    }
</script>

<div class="auth">
    <h1>Sign in</h1>

    {#if totpTicket}
        <form onsubmit={submitTotp} class="card">
            <p class="muted">Enter the 6-digit code from your authenticator app, or a backup code.</p>
            <div class="field">
                <label for="totp">Authenticator code</label>
                <input
                    id="totp"
                    bind:value={totpCode}
                    required
                    autocomplete="one-time-code"
                    inputmode="numeric"
                    placeholder="000000"
                    maxlength={10}
                />
            </div>
            <button type="submit" disabled={busy}>{busy ? 'Verifying…' : 'Verify'}</button>
            <button type="button" class="secondary" onclick={backToLogin}>Back</button>
            {#if error}<p class="error">{error}</p>{/if}
        </form>
    {:else}
        <form onsubmit={submit} class="card">
            <div class="field">
                <label for="u">Username</label>
                <input id="u" bind:value={username} required autocomplete="username" />
            </div>
            <div class="field">
                <label for="p">Password</label>
                <input
                    id="p"
                    type="password"
                    bind:value={password}
                    required
                    autocomplete="current-password"
                />
            </div>
            <button type="submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
            {#if error}<p class="error">{error}</p>{/if}
        </form>

        {#if $publicConfig?.setup_required}
            <div class="setup">
                <p>
                    <strong>First-run setup.</strong> No users exist yet —
                    <a href="/register">create the admin account</a>.
                </p>
            </div>
        {:else if $publicConfig?.registration_enabled}
            <p class="muted">No account? <a href="/register">Register</a></p>
        {/if}

        {#if $publicConfig?.version}
            <p class="version muted">v{$publicConfig.version}</p>
        {/if}

        {#if $publicConfig?.oidc_providers?.length}
            <h3>Or sign in with:</h3>
            <ul>
                {#each $publicConfig.oidc_providers as p}
                    <li><a href={p.login_url}>{p.label}</a></li>
                {/each}
            </ul>
        {/if}
    {/if}
</div>

<style>
    .auth {
        max-width: 400px;
        margin: 4rem auto 0;
    }
    .setup {
        margin-top: 1rem;
        padding: 0.75rem 1rem;
        border: 1px solid var(--accent);
        border-radius: 0.5rem;
        background: color-mix(in srgb, var(--accent) 10%, transparent);
    }
    .version {
        text-align: center;
        font-size: 0.75rem;
        margin-top: 2rem;
    }
</style>
