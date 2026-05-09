<script lang="ts">
    import { goto } from '$app/navigation';
    import { api } from '$lib/api';
    import { refreshMe } from '$lib/session';
    import { _ } from 'svelte-i18n';
    import { locale, LOCALES, setLocale } from '$lib/i18n';
    import { Alert, Button, FormField } from '$lib/components';

    let username = $state('');
    let displayName = $state('');
    let email = $state('');
    let password = $state('');
    let selectedLocale = $state($locale ?? 'en');
    let error = $state('');
    let busy = $state(false);

    async function submit(e: Event) {
        e.preventDefault();
        busy = true;
        error = '';
        try {
            await api.post('/auth/register', {
                username,
                password,
                email: email || null,
                display_name: displayName || null
            }, true);
            await api.post('/auth/login', { username, password }, true);
            // Save locale preference to profile immediately after registration.
            if (selectedLocale && selectedLocale !== 'en') {
                try { await api.patch('/auth/me', { locale: selectedLocale }, true); } catch { /* non-fatal */ }
            }
            setLocale(selectedLocale);
            await refreshMe();
            await goto('/');
        } catch (e) {
            error = (e as Error).message;
        } finally {
            busy = false;
        }
    }
</script>

<div class="auth">
    <img src="/branding/logo-stacked-light.png" alt="Tangible" class="auth-logo" />
    <h1>{$_('auth.register')}</h1>
    <form onsubmit={submit} class="card">
        <FormField label={$_('auth.username')} for="u" required>
            <input id="u" bind:value={username} required autocomplete="username" />
        </FormField>
        <FormField label="{$_('auth.display_name')} ({$_('auth.optional')})" for="n">
            <input id="n" bind:value={displayName} autocomplete="name" />
        </FormField>
        <FormField label="{$_('auth.email')} ({$_('auth.optional')})" for="e">
            <input id="e" type="email" bind:value={email} autocomplete="email" />
        </FormField>
        <FormField label={$_('auth.password')} for="p" hint="At least 12 characters" required>
            <input
                id="p"
                type="password"
                bind:value={password}
                required
                minlength="12"
                autocomplete="new-password"
            />
        </FormField>
        <FormField label={$_('lang.label')} for="lang">
            <select id="lang" bind:value={selectedLocale} onchange={() => setLocale(selectedLocale)}>
                {#each LOCALES as loc}
                    <option value={loc.code}>{loc.label}</option>
                {/each}
            </select>
        </FormField>
        {#if error}
            <Alert variant="danger" dismissible onclose={() => (error = '')}>{error}</Alert>
        {/if}
        <Button type="submit" loading={busy} style="width:100%">{busy ? $_('auth.registering') : $_('auth.register')}</Button>
    </form>
    <p class="muted">{$_('auth.already_have_account')} <a href="/login">{$_('auth.sign_in_link')}</a></p>
</div>

<style>
    .auth {
        max-width: 400px;
        margin: 4rem auto 0;
    }
    .auth form.card {
        display: flex;
        flex-direction: column;
        gap: var(--space-4);
    }
    .auth-logo {
        display: block;
        margin: 0 auto 1.5rem;
        width: 180px;
        height: auto;
        content: url('/branding/logo-stacked-light.png');
    }
    :global([data-theme$="-dark"]) .auth-logo {
        content: url('/branding/logo-stacked-dark.png');
    }
</style>
