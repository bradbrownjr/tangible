<script lang="ts">
    import { goto } from '$app/navigation';
    import { api } from '$lib/api';
    import { refreshMe } from '$lib/session';
    import { _ } from 'svelte-i18n';

    let username = $state('');
    let displayName = $state('');
    let email = $state('');
    let password = $state('');
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
            });
            await api.post('/auth/login', { username, password });
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
    <h1>{$_('auth.register')}</h1>
    <form onsubmit={submit} class="card">
        <div class="field">
            <label for="u">{$_('auth.username')}</label>
            <input id="u" bind:value={username} required autocomplete="username" />
        </div>
        <div class="field">
            <label for="n">{$_('auth.display_name')} <span class="muted">({$_('auth.optional')})</span></label>
            <input id="n" bind:value={displayName} autocomplete="name" />
        </div>
        <div class="field">
            <label for="e">{$_('auth.email')} <span class="muted">({$_('auth.optional')})</span></label>
            <input id="e" type="email" bind:value={email} autocomplete="email" />
        </div>
        <div class="field">
            <label for="p">{$_('auth.password')}</label>
            <input
                id="p"
                type="password"
                bind:value={password}
                required
                minlength="12"
                autocomplete="new-password"
            />
        </div>
        <button type="submit" disabled={busy}>{busy ? $_('auth.registering') : $_('auth.register')}</button>
        {#if error}<p class="error">{error}</p>{/if}
    </form>
    <p class="muted">{$_('auth.already_have_account')} <a href="/login">{$_('auth.sign_in_link')}</a></p>
</div>

<style>
    .auth {
        max-width: 400px;
        margin: 4rem auto 0;
    }
</style>
