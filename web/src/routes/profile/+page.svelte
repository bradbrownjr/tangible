<script lang="ts">
    import { api, type User } from '$lib/api';
    import { me, refreshMe } from '$lib/session';
    import { _ } from 'svelte-i18n';
    import { Alert, Button, FormField } from '$lib/components';

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
            <FormField label={$_('profile.username_label')} hint={$_('profile.username_hint')}>
                <input value={$me.username} readonly />
            </FormField>
            <FormField label={$_('profile.full_name_label')} for="n" hint={$_('profile.full_name_hint')}>
                <input id="n" bind:value={displayName} autocomplete="name" />
            </FormField>
            <FormField label={$_('profile.email_label')} for="e">
                <input id="e" type="email" bind:value={email} autocomplete="email" />
            </FormField>
            <FormField label={$_('profile.new_password_label')} for="p" hint={$_('profile.new_password_hint')}>
                <input
                    id="p"
                    type="password"
                    bind:value={password}
                    minlength="12"
                    autocomplete="new-password"
                />
            </FormField>
            {#if saved}
                <Alert variant="success" dismissible onclose={() => (saved = false)}>{$_('profile.saved')}</Alert>
            {/if}
            {#if error}
                <Alert variant="danger" dismissible onclose={() => (error = '')}>{error}</Alert>
            {/if}
            <Button type="submit" loading={busy} style="width:100%">{busy ? $_('profile.saving') : $_('profile.save')}</Button>
        </form>
    {/if}
</div>

<style>
    .profile {
        max-width: 480px;
        margin: 2rem auto;
    }
</style>
