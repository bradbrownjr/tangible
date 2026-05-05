<script lang="ts">
    import { goto } from '$app/navigation';
    import { api } from '$lib/api';
    import { publicConfig, refreshMe } from '$lib/session';
    import { _ } from 'svelte-i18n';
    import { Alert, Button, FormField } from '$lib/components';
    import Icon from '$lib/Icon.svelte';

    let username = $state('');
    let password = $state('');
    let showPassword = $state(false);
    let totpCode = $state('');
    let totpTicket = $state<string | null>(null);
    let error = $state('');
    let busy = $state(false);

    async function submit(e: Event) {
        e.preventDefault();
        busy = true;
        error = '';
        try {
            const res = await api.post<{ totp_required?: boolean; ticket?: string }>('/auth/login', { username, password }, true);
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
            await api.post('/auth/totp/confirm-login', { ticket: totpTicket, code: totpCode }, true);
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
    <h1>{$_('auth.sign_in')}</h1>

    {#if totpTicket}
        <form onsubmit={submitTotp} class="card">
            <p class="muted">{$_('auth.totp_enter_code')}</p>
            <FormField label={$_('auth.authenticator_code')} for="totp">
                <input
                    id="totp"
                    bind:value={totpCode}
                    required
                    autocomplete="one-time-code"
                    inputmode="numeric"
                    placeholder="000000"
                    maxlength={10}
                />
            </FormField>
            {#if error}
                <Alert variant="danger" dismissible onclose={() => (error = '')}>{error}</Alert>
            {/if}
            <Button type="submit" loading={busy} style="width:100%">{busy ? $_('auth.verifying') : $_('auth.verify')}</Button>
            <Button type="button" variant="secondary" onclick={backToLogin} style="width:100%">{$_('auth.back')}</Button>
        </form>
    {:else}
        <form onsubmit={submit} class="card">
            <FormField label={$_('auth.username')} for="u">
                <input id="u" bind:value={username} required autocomplete="username" />
            </FormField>
            <FormField label={$_('auth.password')} for="p">
                <div class="pw-field">
                    <input
                        id="p"
                        type={showPassword ? 'text' : 'password'}
                        bind:value={password}
                        required
                        autocomplete="current-password"
                    />
                    <button
                        type="button"
                        class="pw-toggle"
                        onclick={() => (showPassword = !showPassword)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                        <Icon name={showPassword ? 'eye-off' : 'eye'} size={16} />
                    </button>
                </div>
            </FormField>
            {#if error}
                <Alert variant="danger" dismissible onclose={() => (error = '')}>{error}</Alert>
            {/if}
            <Button type="submit" loading={busy} style="width:100%">{busy ? $_('auth.signing_in') : $_('auth.sign_in')}</Button>
        </form>

        {#if $publicConfig?.setup_required}
            <div class="setup">
                <p>
                    <strong>{$_('auth.first_run_setup')}.</strong> {$_('auth.create_admin_account')}
                    <a href="/register">{$_('auth.register_link')}</a>.
                </p>
            </div>
        {:else if $publicConfig?.registration_enabled}
            <p class="muted">{$_('auth.no_account')} <a href="/register">{$_('auth.register_link')}</a></p>
        {/if}

        {#if $publicConfig?.version}
            <p class="version muted">v{$publicConfig.version}</p>
        {/if}

        {#if $publicConfig?.oidc_providers?.length}
            <div class="oidc-section">
                <p class="oidc-label muted">— {$_('auth.sign_in')} —</p>
                <div class="oidc-pills">
                    {#each $publicConfig.oidc_providers as p}
                        <a href={p.login_url} class="oidc-pill">{p.label}</a>
                    {/each}
                </div>
            </div>
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
    .pw-field {
        position: relative;
    }
    .pw-toggle {
        position: absolute;
        right: 0.4rem;
        top: 50%;
        translate: 0 -50%;
        background: transparent;
        border: none;
        padding: 0.2rem;
        min-height: auto;
        color: var(--text-muted);
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        border-radius: var(--radius-sm);
    }
    .pw-toggle:hover { color: var(--text); }
    .oidc-section {
        margin-top: 1.5rem;
        text-align: center;
    }
    .oidc-label {
        font-size: 0.8rem;
        margin-bottom: 0.75rem;
    }
    .oidc-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: center;
    }
    .oidc-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.45rem 1rem;
        border: 1px solid var(--border);
        border-radius: var(--radius-full);
        background: var(--surface-2);
        color: var(--text);
        text-decoration: none;
        font-size: 0.875rem;
        transition: background 0.15s, border-color 0.15s;
    }
    .oidc-pill:hover {
        background: color-mix(in srgb, var(--accent) 12%, var(--surface-2));
        border-color: var(--accent);
        color: var(--accent);
    }
</style>
