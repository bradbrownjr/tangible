<script lang="ts">
    import { onMount } from 'svelte';
    import { api } from '$lib/api';
    import { _ } from 'svelte-i18n';
    import { ConfirmDialog, Modal } from '$lib/components';

    interface Token {
        id: string;
        name: string;
        token: string | null;
        last_used_at: string | null;
        expires_at: string | null;
        created_at: string;
    }

    interface TOTPStatus { enabled: boolean; backup_codes_remaining: number; }
    interface TOTPSetup  { secret: string; qr_uri: string; qr_png_b64: string; }

    let tokens          = $state<Token[]>([]);
    let newName         = $state('');
    let issuedRaw       = $state('');
    let revokeTokenId   = $state<string | null>(null);
    let error           = $state('');

    let totpStatus      = $state<TOTPStatus | null>(null);
    let totpSetup       = $state<TOTPSetup | null>(null);
    let totpSetupCode   = $state('');
    let totpSetupMsg    = $state('');
    let totpBackupCodes = $state<string[]>([]);
    let totpDisableOpen = $state(false);
    let totpDisablePassword = $state('');
    let totpDisableCode = $state('');
    let totpRegenOpen   = $state(false);
    let totpRegenCode   = $state('');

    async function loadTokens() {
        try {
            tokens = await api.get<Token[]>('/auth/tokens');
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function loadTotpStatus() {
        try {
            totpStatus = await api.get<TOTPStatus>('/auth/totp');
        } catch { /* not critical */ }
    }

    async function createToken(e: Event) {
        e.preventDefault();
        if (!newName.trim()) return;
        try {
            const params = new URLSearchParams({ name: newName.trim() });
            const t = await api.post<Token>(`/auth/tokens?${params.toString()}`, undefined);
            issuedRaw = t.token ?? '';
            newName = '';
            await loadTokens();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function revokeConfirmed() {
        if (!revokeTokenId) return;
        await api.delete(`/auth/tokens/${revokeTokenId}`);
        revokeTokenId = null;
        await loadTokens();
    }

    async function startTotpSetup() {
        totpSetupMsg = '';
        totpSetup = null;
        try {
            totpSetup = await api.post<TOTPSetup>('/auth/totp/setup', undefined);
        } catch (e) {
            totpSetupMsg = (e as Error).message;
        }
    }

    async function verifyTotpSetup() {
        if (!totpSetupCode.trim()) return;
        try {
            const res = await api.post<{ enabled: boolean; backup_codes: string[] }>(
                '/auth/totp/verify', { code: totpSetupCode }
            );
            totpBackupCodes = res.backup_codes;
            totpSetup = null;
            totpSetupCode = '';
            await loadTotpStatus();
        } catch (e) {
            totpSetupMsg = (e as Error).message;
        }
    }

    async function disableTotp() {
        try {
            await fetch('/api/auth/totp', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: totpDisablePassword, totp_code: totpDisableCode || null }),
                credentials: 'include',
            });
        } catch { /* ignore */ }
        totpDisableOpen = false;
        totpDisablePassword = '';
        totpDisableCode = '';
        await loadTotpStatus();
    }

    async function regenBackupCodes() {
        try {
            const res = await api.post<{ backup_codes: string[] }>(
                '/auth/totp/regenerate-backup-codes', { code: totpRegenCode }
            );
            totpBackupCodes = res.backup_codes;
            totpRegenOpen = false;
            totpRegenCode = '';
            await loadTotpStatus();
        } catch (e) {
            error = (e as Error).message;
        }
    }

    import { page } from '$app/state';
    import { me } from '$lib/session';

    const enrollRequired = $derived(!!$me?.enrollment_required);
    const enrollParam = $derived(page.url.searchParams.has('enroll'));

    onMount(async () => {
        await Promise.all([loadTokens(), loadTotpStatus()]);
        if ((enrollRequired || enrollParam) && !totpStatus?.enabled && !totpSetup) {
            await startTotpSetup();
        }
    });
</script>

<h2>{$_('settings.nav_security')}</h2>

{#if error}<p class="error">{error}</p>{/if}

<!-- API Tokens -->
<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">{$_('settings.api_tokens_heading')}</h3>
    <p class="muted">{$_('settings.api_tokens_description')}</p>

    <form onsubmit={createToken} style="display:flex; gap:.5rem; margin-bottom:1rem">
        <input bind:value={newName} placeholder={$_('settings.token_name_placeholder')} />
        <button type="submit">{$_('settings.create_token_button')}</button>
    </form>

    {#if issuedRaw}
        <div class="card" style="background: var(--surface-2); margin-bottom: 1rem">
            <p><strong>{$_('settings.token_save_message')}</strong></p>
            <pre style="word-break: break-all; white-space: pre-wrap">{issuedRaw}</pre>
            <button class="secondary" onclick={() => (issuedRaw = '')}>{$_('settings.token_dismiss_button')}</button>
        </div>
    {/if}

    {#if tokens.length === 0}
        <p class="muted">{$_('settings.no_tokens')}</p>
    {:else}
        <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>{$_('settings.token_col_name')}</th>
                    <th>{$_('settings.token_col_last_used')}</th>
                    <th>{$_('settings.token_col_expires')}</th>
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
                            <button class="danger" onclick={() => (revokeTokenId = t.id)}>{$_('settings.token_revoke_button')}</button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
        </div>
    {/if}
</div>

<!-- TOTP 2FA -->
<div class="card">
    <h3 style="margin-top:0">{$_('settings.totp_heading')}</h3>

    {#if totpStatus?.enabled}
        <p class="muted">{$_('settings.totp_enabled_message', { values: { count: totpStatus.backup_codes_remaining } })}</p>
        {#if totpBackupCodes.length}
            <div class="card" style="background: var(--surface-2); margin-bottom: 0.75rem">
                <p><strong>{$_('settings.backup_codes_heading')}</strong></p>
                <ul class="backup-codes">
                    {#each totpBackupCodes as c (c)}<li><code>{c}</code></li>{/each}
                </ul>
                <button class="secondary" onclick={() => (totpBackupCodes = [])}>{$_('settings.backup_codes_dismiss')}</button>
            </div>
        {/if}
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap">
            <button class="secondary" onclick={() => (totpRegenOpen = true)}>{$_('settings.totp_regen_button')}</button>
            <button class="danger" onclick={() => (totpDisableOpen = true)}>{$_('settings.totp_disable_button')}</button>
        </div>
    {:else if totpSetup}
        <p class="muted">{$_('settings.totp_setup_message')}</p>
        <img src="data:image/png;base64,{totpSetup.qr_png_b64}" alt="TOTP QR code"
            style="display:block; margin: 0.75rem 0; max-width:200px; image-rendering:pixelated" />
        <p class="muted">{$_('settings.totp_secret_label')} <code>{totpSetup.secret}</code></p>
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap">
            <input bind:value={totpSetupCode} placeholder={$_('settings.totp_code_placeholder')}
                maxlength={6} inputmode="numeric" autocomplete="one-time-code" style="width:9rem" />
            <button onclick={verifyTotpSetup}>{$_('settings.totp_activate_button')}</button>
            <button class="secondary" onclick={() => { totpSetup = null; totpSetupCode = ''; }}>{$_('common.cancel')}</button>
        </div>
        {#if totpSetupMsg}<p class="error">{totpSetupMsg}</p>{/if}
    {:else}
        <p class="muted">{$_('settings.totp_disabled_message')}</p>
        <button onclick={startTotpSetup}>{$_('settings.totp_setup_button')}</button>
        {#if totpSetupMsg}<p class="error">{totpSetupMsg}</p>{/if}
    {/if}
</div>

<!-- Revoke token dialog -->
<ConfirmDialog
    open={!!revokeTokenId}
    title={$_('settings.revoke_token_title')}
    variant="danger"
    confirmLabel={$_('settings.revoke_token_confirm')}
    onconfirm={revokeConfirmed}
    oncancel={() => (revokeTokenId = null)}
>
    {$_('settings.revoke_token_text')}
</ConfirmDialog>

<!-- Disable TOTP modal -->
<Modal open={totpDisableOpen} title={$_('settings.totp_disable_title')} onclose={() => (totpDisableOpen = false)}>
    <p class="muted">{$_('settings.totp_disable_text')}</p>
    <div class="field"><label>{$_('settings.totp_disable_password_label')}<input type="password" bind:value={totpDisablePassword} autocomplete="current-password" /></label></div>
    <div class="field"><label>{$_('settings.totp_disable_code_label')}<input bind:value={totpDisableCode} maxlength={10} inputmode="numeric" placeholder={$_('settings.totp_disable_code_placeholder')} /></label></div>
    {#snippet footer()}
        <button type="button" class="secondary" onclick={() => (totpDisableOpen = false)}>{$_('common.cancel')}</button>
        <button type="button" class="danger" onclick={disableTotp}>{$_('settings.totp_disable_confirm')}</button>
    {/snippet}
</Modal>

<!-- Regenerate backup codes modal -->
<Modal open={totpRegenOpen} title={$_('settings.totp_regen_title')} onclose={() => (totpRegenOpen = false)}>
    <p class="muted">{$_('settings.totp_regen_text')}</p>
    <div class="field"><label>{$_('settings.totp_disable_code_label')}<input bind:value={totpRegenCode} maxlength={10} inputmode="numeric" placeholder={$_('settings.totp_regen_code_placeholder')} /></label></div>
    {#snippet footer()}
        <button type="button" class="secondary" onclick={() => (totpRegenOpen = false)}>{$_('common.cancel')}</button>
        <button type="button" onclick={regenBackupCodes}>{$_('settings.totp_regen_confirm')}</button>
    {/snippet}
</Modal>

<style>
    h2 { margin-top: 0; }

    .backup-codes {
        list-style: none;
        padding: 0;
        display: flex;
        flex-wrap: wrap;
        gap: 0.35rem;
        margin: 0.5rem 0;
    }
    .backup-codes li code {
        font-size: 0.85rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 0.2rem 0.45rem;
        letter-spacing: 0.05em;
    }

    .field { display: grid; gap: 0.25rem; }
    .field label { font-size: 0.875rem; font-weight: 500; }
    .field input { width: 100%; }
</style>
