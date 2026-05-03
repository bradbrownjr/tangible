<script lang="ts">
    import { api, type User } from '$lib/api';
    import { me, refreshMe } from '$lib/session';
    import { _ } from 'svelte-i18n';

    let displayName = $state($me ? ($me.display_name ?? '') : '');
    let email = $state($me ? ($me.email ?? '') : '');
    let password = $state('');
    let busy = $state(false);
    let error = $state('');
    let saved = $state(false);

    // Keep form in sync if $me loads after mount.
    $effect(() => {
        if ($me) {
            displayName = $me.display_name ?? '';
            email = $me.email ?? '';
        }
    });

    async function submit(e: Event) {
        e.preventDefault();
        busy = true;
        error = '';
        saved = false;
        try {
            const body: Record<string, unknown> = {
                display_name: displayName,
                email: email || null,
            };
            if (password) body.password = password;
            await api.patch<User>('/auth/me', body);
            await refreshMe();
            password = '';
            saved = true;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            busy = false;
        }
    }
</script>

<div class="profile">
    <h1>{$_('profile.title')}</h1>
    {#if !$me}
        <p class="muted">{$_('common.loading')}</p>
    {:else}
        <form onsubmit={submit} class="card">
            <div class="field">
                <label>{$_('profile.username_label')}</label>
                <input value={$me.username} disabled />
                <p class="muted hint">{$_('profile.username_hint')}</p>
            </div>
            <div class="field">
                <label for="n">{$_('profile.full_name_label')}</label>
                <input id="n" bind:value={displayName} autocomplete="name" />
                <p class="muted hint">{$_('profile.full_name_hint')}</p>
            </div>
            <div class="field">
                <label for="e">{$_('profile.email_label')}</label>
                <input id="e" type="email" bind:value={email} autocomplete="email" />
            </div>
            <div class="field">
                <label for="p">{$_('profile.new_password_label')} <span class="muted">({$_('profile.new_password_hint')})</span></label>
                <input
                    id="p"
                    type="password"
                    bind:value={password}
                    minlength="12"
                    autocomplete="new-password"
                />
            </div>
            <button type="submit" disabled={busy}>{busy ? $_('profile.saving') : $_('profile.save')}</button>
            {#if saved}<p class="ok">{$_('profile.saved')}</p>{/if}
            {#if error}<p class="error">{error}</p>{/if}
        </form>
    {/if}
</div>

<style>
    .profile {
        max-width: 480px;
        margin: 2rem auto;
    }
    .hint {
        font-size: 0.8rem;
        margin: 0.25rem 0 0;
    }
    .ok {
        color: var(--success, #22c55e);
    }
</style>

