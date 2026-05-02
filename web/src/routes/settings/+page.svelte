<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, type SiteSetting } from '$lib/api';
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

    interface NotificationPref {
        kind: string;
        email_enabled: boolean;
        push_enabled: boolean;
        browser_enabled: boolean;
        lead_days: number;
    }

    const KIND_LABELS: Record<string, string> = {
        maintenance_due: 'Maintenance due',
        chore_due: 'Chore due',
        item_use_by: 'Item use-by',
        item_expires: 'Item expires',
        lot_use_by: 'Package use-by',
        low_stock: 'Low stock'
    };

    let tokens = $state<Token[]>([]);
    let alerts = $state<DueAlert[]>([]);
    let notifPrefs = $state<NotificationPref[]>([]);
    let digestQueued = $state(false);
    let digestMessage = $state('');
    let newName = $state('');
    let issuedRaw = $state('');
    let error = $state('');
    let revokeModalTokenId = $state<string | null>(null);
    let scrubModalOpen = $state(false);
    let scrubConfirmText = $state('');
    let scrubResult = $state('');
    const scrubPhrase = 'SCRUB INVENTORY';

    // 2FA state
    interface TOTPStatus { enabled: boolean; backup_codes_remaining: number; }
    interface TOTPSetup { secret: string; qr_uri: string; qr_png_b64: string; }
    let totpStatus = $state<TOTPStatus | null>(null);
    let totpSetup = $state<TOTPSetup | null>(null);
    let totpSetupCode = $state('');
    let totpSetupMessage = $state('');
    let totpBackupCodes = $state<string[]>([]);
    let totpDisableOpen = $state(false);
    let totpDisablePassword = $state('');
    let totpDisableCode = $state('');
    let totpRegenCode = $state('');
    let totpRegenOpen = $state(false);

    // Account state
    let deleteAccountOpen = $state(false);
    let deletePassword = $state('');
    let deleteTotpCode = $state('');
    let deleteMessage = $state('');

    // Admin settings state
    let siteSettings = $state<SiteSetting[]>([]);
    let siteSettingsEdits = $state<Record<string, string>>({});
    let siteSettingsSaved = $state(false);
    let siteSettingsError = $state('');
    let siteSettingsLoaded = $state(false);

    // Enrollment enforcement
    const enrollRequired = $derived(!!$me?.enrollment_required);
    const enrollParam = $derived(page.url.searchParams.has('enroll'));

    async function load() {
        try {
            [tokens, alerts, notifPrefs] = await Promise.all([
                api.get<Token[]>('/auth/tokens'),
                api.get<DueAlert[]>('/alerts?within_days=14'),
                api.get<NotificationPref[]>('/notifications')
            ]);
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function saveNotifPref(kind: string, updates: Partial<Omit<NotificationPref, 'kind'>>) {
        try {
            const current = notifPrefs.find(p => p.kind === kind)!;
            const payload = {
                email_enabled: current.email_enabled,
                push_enabled: current.push_enabled,
                browser_enabled: current.browser_enabled,
                lead_days: current.lead_days,
                ...updates,
            };
            const updated = await api.put<NotificationPref>(`/notifications/${kind}`, payload);
            notifPrefs = notifPrefs.map(p => p.kind === kind ? updated : p);
        } catch (e) {
            error = (e as Error).message;
        }
    }

    async function requestBrowserPermission() {
        if (typeof Notification === 'undefined') {
            digestMessage = 'Browser notifications are not supported in this browser.';
            return;
        }
        const perm = await Notification.requestPermission();
        digestMessage = perm === 'granted'
            ? 'Browser notifications enabled.'
            : 'Permission denied — check your browser settings.';
    }

    async function sendDigest() {
        digestMessage = '';
        digestQueued = false;
        try {
            const res = await api.post<{ queued: boolean; count?: number; reason?: string }>('/notifications/send-digest', undefined);
            if (res.queued) {
                digestQueued = true;
                digestMessage = `Digest queued — ${res.count} alert${res.count !== 1 ? 's' : ''} will be emailed to you shortly.`;
            } else {
                digestMessage = res.reason === 'no_alerts' ? 'No alerts match your enabled preferences right now.' : 'No notification preferences enabled.';
            }
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

    // --- 2FA helpers ---
    async function loadTotpStatus() {
        try {
            totpStatus = await api.get<TOTPStatus>('/auth/totp');
        } catch { /* not critical */ }
    }

    async function startTotpSetup() {
        totpSetupMessage = '';
        totpSetup = null;
        try {
            totpSetup = await api.post<TOTPSetup>('/auth/totp/setup', undefined);
        } catch (e) {
            totpSetupMessage = (e as Error).message;
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
            totpSetupMessage = (e as Error).message;
        }
    }

    async function disableTotp() {
        try {
            await api.delete(`/auth/totp?password=${encodeURIComponent(totpDisablePassword)}&totp_code=${encodeURIComponent(totpDisableCode)}`);
        } catch {
            // delete with body requires fetch directly
            await fetch('/api/auth/totp', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: totpDisablePassword, totp_code: totpDisableCode || null }),
                credentials: 'include',
            });
        }
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

    // --- Account helpers ---
    async function exportAccount() {
        window.location.href = '/api/auth/me/export';
    }

    async function deleteAccount() {
        try {
            await fetch('/api/auth/me', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: deletePassword, totp_code: deleteTotpCode || null }),
                credentials: 'include',
            });
            window.location.href = '/login';
        } catch (e) {
            deleteMessage = (e as Error).message;
        }
    }

    // --- Admin site settings ---
    async function loadSiteSettings() {
        try {
            siteSettings = await api.get<SiteSetting[]>('/admin/system/settings');
            siteSettingsEdits = {};
            siteSettingsLoaded = true;
        } catch { /* non-admin or unavailable */ }
    }

    function siteSettingDisplayValue(s: SiteSetting): string {
        if (s.value === null) return '';
        return s.value === '***' ? '' : s.value;
    }

    function siteSettingPlaceholder(s: SiteSetting): string {
        if (s.value === '***') return 'Enter new value to change, or leave blank to keep current';
        if (s.source !== 'default' && s.value !== null && !s.sensitive) return s.value;
        return s.type === 'bool' ? 'true or false' : s.type === 'int' ? String(s.value ?? '') : '';
    }

    async function saveSiteSettings() {
        siteSettingsError = '';
        siteSettingsSaved = false;
        const updates: Record<string, string | null> = {};
        for (const [key, val] of Object.entries(siteSettingsEdits)) {
            updates[key] = val.trim() === '' ? null : val.trim();
        }
        // For sensitive fields left blank but already set, send "***" sentinel
        for (const s of siteSettings) {
            if (s.sensitive && s.is_set && !(s.key in updates)) {
                updates[s.key] = '***';
            }
        }
        try {
            siteSettings = await api.put<SiteSetting[]>('/admin/system/settings', { updates });
            siteSettingsEdits = {};
            siteSettingsSaved = true;
            // Reload public config so require_2fa changes take effect
            await refreshMe();
        } catch (e) {
            siteSettingsError = (e as Error).message;
        }
    }

    async function clearSiteSetting(key: string) {
        try {
            await fetch(`/api/admin/system/settings/${encodeURIComponent(key)}`, {
                method: 'DELETE',
                credentials: 'include',
            });
            await loadSiteSettings();
        } catch (e) {
            siteSettingsError = (e as Error).message;
        }
    }

    // Group settings by section for display
    const SECTION_LABELS: Record<string, string> = {
        security: 'Security',
        sessions: 'Sessions',
        integrations: 'Integrations',
        email: 'Email / SMTP',
    };

    onMount(async () => {
        await refreshMe();
        const promises: Promise<unknown>[] = [load(), loadTotpStatus()];
        if ($me?.is_admin) promises.push(loadSiteSettings());
        await Promise.all(promises);
        // Auto-open 2FA setup when enrollment is required or ?enroll param is set
        if ((enrollRequired || enrollParam) && !totpStatus?.enabled && !totpSetup) {
            await startTotpSetup();
        }
    });
</script>

<h1>Settings</h1>

{#if enrollRequired || enrollParam}
    <div class="banner-warn" role="alert">
        <strong>Two-factor authentication required.</strong>
        Your administrator requires 2FA for all accounts. Please set it up below before you can continue.
    </div>
{/if}

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
    <p class="muted">Choose how Tangible looks. "System" follows your OS setting.</p>
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

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">Notifications</h3>
    <p class="muted">Choose how you're notified per alert type. Email requires SMTP configured on the server. Browser notifications require permission (prompted below). App notifications appear daily on your Android device.</p>
    {#if notifPrefs.length > 0}
        <table class="notif-table">
            <thead>
                <tr>
                    <th>Alert type</th>
                    <th title="Send email digest">Email</th>
                    <th title="Browser notification when the app is open">Browser</th>
                    <th title="Daily notification on the Android app">App</th>
                    <th>Lead time (days)</th>
                </tr>
            </thead>
            <tbody>
                {#each notifPrefs as p (p.kind)}
                    <tr>
                        <td>{KIND_LABELS[p.kind] ?? p.kind}</td>
                        <td>
                            <input
                                type="checkbox"
                                checked={p.email_enabled}
                                onchange={(e) => saveNotifPref(p.kind, { email_enabled: (e.target as HTMLInputElement).checked })}
                            />
                        </td>
                        <td>
                            <input
                                type="checkbox"
                                checked={p.browser_enabled}
                                onchange={(e) => saveNotifPref(p.kind, { browser_enabled: (e.target as HTMLInputElement).checked })}
                            />
                        </td>
                        <td>
                            <input
                                type="checkbox"
                                checked={p.push_enabled}
                                onchange={(e) => saveNotifPref(p.kind, { push_enabled: (e.target as HTMLInputElement).checked })}
                            />
                        </td>
                        <td>
                            <input
                                type="number"
                                min="1"
                                max="365"
                                value={p.lead_days}
                                style="width:5rem"
                                onchange={(e) => saveNotifPref(p.kind, { lead_days: parseInt((e.target as HTMLInputElement).value) || 7 })}
                            />
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
    <div style="margin-top:0.75rem;display:flex;gap:0.75rem;align-items:center;flex-wrap:wrap">
        <button onclick={sendDigest}>Send email digest now</button>
        <button class="secondary" onclick={requestBrowserPermission}>Enable browser notifications</button>
        {#if digestMessage}
            <span class={digestQueued ? 'ok' : 'muted'}>{digestMessage}</span>
        {/if}
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

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">Two-factor authentication</h3>
    {#if totpStatus?.enabled}
        <p class="muted">2FA is <strong>enabled</strong>. Backup codes remaining: {totpStatus.backup_codes_remaining}.</p>
        {#if totpBackupCodes.length}
            <div class="card" style="background: var(--surface-2); margin-bottom: 0.75rem">
                <p><strong>Save these backup codes — they won't be shown again:</strong></p>
                <ul class="backup-codes">
                    {#each totpBackupCodes as c (c)}<li><code>{c}</code></li>{/each}
                </ul>
                <button class="secondary" onclick={() => (totpBackupCodes = [])}>Dismiss</button>
            </div>
        {/if}
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap">
            <button class="secondary" onclick={() => (totpRegenOpen = true)}>Regenerate backup codes</button>
            <button class="danger" onclick={() => (totpDisableOpen = true)}>Disable 2FA</button>
        </div>
    {:else if totpSetup}
        <p class="muted">Scan the QR code with your authenticator app, then enter the 6-digit code to activate.</p>
        <img src="data:image/png;base64,{totpSetup.qr_png_b64}" alt="TOTP QR code" style="display:block; margin: 0.75rem 0; max-width:200px; image-rendering:pixelated" />
        <p class="muted">Or enter the secret manually: <code>{totpSetup.secret}</code></p>
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap">
            <input bind:value={totpSetupCode} placeholder="6-digit code" maxlength={6} inputmode="numeric" autocomplete="one-time-code" style="width:9rem" />
            <button onclick={verifyTotpSetup}>Activate 2FA</button>
            <button class="secondary" onclick={() => { totpSetup = null; totpSetupCode = ''; }}>Cancel</button>
        </div>
        {#if totpSetupMessage}<p class="error">{totpSetupMessage}</p>{/if}
    {:else}
        <p class="muted">Add a second factor to protect your account. You'll need an authenticator app (Google Authenticator, Authy, etc.).</p>
        <button onclick={startTotpSetup}>Set up 2FA</button>
        {#if totpSetupMessage}<p class="error">{totpSetupMessage}</p>{/if}
    {/if}
</div>

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">Account</h3>
    <p class="muted">Export all your data or permanently delete your account.</p>
    <div style="display:flex; gap:0.5rem; flex-wrap:wrap">
        <button class="secondary" onclick={exportAccount}>Export my data</button>
        <button class="danger" onclick={() => (deleteAccountOpen = true)}>Delete account</button>
    </div>
</div>

{#if $me?.is_admin}
    {#if siteSettingsLoaded}
        <div class="card" style="margin-top: 1rem">
            <h3 style="margin-top:0">Server Settings</h3>
            <p class="muted">
                These override environment variables at runtime. Values set here take precedence
                over Docker/env config without requiring a restart.
                <span class="muted" style="font-size:0.8rem">Env vars shown as source indicator only.</span>
            </p>
            {#each Object.entries(SECTION_LABELS) as [section, label] (section)}
                {@const group = siteSettings.filter(s => s.section === section)}
                {#if group.length}
                    <h4 style="margin:1rem 0 0.5rem">{label}</h4>
                    <div class="settings-grid">
                        {#each group as s (s.key)}
                            <div class="setting-row">
                                <div class="setting-meta">
                                    <span class="setting-key">{s.key}</span>
                                    {#if s.env_var}
                                        <code class="env-var">{s.env_var}</code>
                                    {/if}
                                    <span class="source-badge source-{s.source}">{s.source}</span>
                                </div>
                                <p class="setting-desc muted">{s.description}</p>
                                <div class="setting-input">
                                    {#if s.type === 'bool'}
                                        <select
                                            value={s.key in siteSettingsEdits ? siteSettingsEdits[s.key] : (s.source === 'default' ? '' : (s.value ?? ''))}
                                            onchange={(e) => (siteSettingsEdits[s.key] = (e.target as HTMLSelectElement).value)}
                                        >
                                            <option value="">(use {s.source === 'database' ? 'env/default' : 'default'})</option>
                                            <option value="true">true</option>
                                            <option value="false">false</option>
                                        </select>
                                    {:else}
                                        <div class="sensitive-wrap">
                                            {#if s.sensitive && s.is_set && !(s.key in siteSettingsEdits)}
                                                <span class="set-badge" title="A value is stored — it is never sent to the browser">Set</span>
                                            {/if}
                                            <input
                                                type={s.sensitive ? 'password' : 'text'}
                                                autocomplete="off"
                                                value={s.key in siteSettingsEdits ? siteSettingsEdits[s.key] : siteSettingDisplayValue(s)}
                                                placeholder={siteSettingPlaceholder(s)}
                                                oninput={(e) => (siteSettingsEdits[s.key] = (e.target as HTMLInputElement).value)}
                                            />
                                        </div>
                                    {/if}
                                    {#if s.source === 'database'}
                                        <button class="secondary small" title="Revert to env/default" onclick={() => clearSiteSetting(s.key)}>Revert</button>
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                {/if}
            {/each}
            {#if siteSettingsError}<p class="error">{siteSettingsError}</p>{/if}
            {#if siteSettingsSaved}<p class="ok">Settings saved.</p>{/if}
            <div style="margin-top:1rem;display:flex;gap:0.5rem">
                <button onclick={saveSiteSettings}>Save settings</button>
                <button class="secondary" onclick={loadSiteSettings}>Reset</button>
            </div>
        </div>
    {/if}
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

{#if totpDisableOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (totpDisableOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="totp-disable-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="totp-disable-title">Disable two-factor authentication?</h3>
            <p class="muted">Enter your password and current authenticator code to disable 2FA.</p>
            <div class="field"><label>Password<input type="password" bind:value={totpDisablePassword} autocomplete="current-password" /></label></div>
            <div class="field"><label>Authenticator code<input bind:value={totpDisableCode} maxlength={10} inputmode="numeric" placeholder="000000" /></label></div>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (totpDisableOpen = false)}>Cancel</button>
                <button type="button" class="danger" onclick={disableTotp}>Disable 2FA</button>
            </div>
        </div>
    </div>
{/if}

{#if totpRegenOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (totpRegenOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="totp-regen-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="totp-regen-title">Regenerate backup codes?</h3>
            <p class="muted">Old backup codes will be invalidated. Enter your current authenticator code to confirm.</p>
            <div class="field"><label>Authenticator code<input bind:value={totpRegenCode} maxlength={10} inputmode="numeric" placeholder="000000" /></label></div>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (totpRegenOpen = false)}>Cancel</button>
                <button type="button" onclick={regenBackupCodes}>Regenerate</button>
            </div>
        </div>
    </div>
{/if}

{#if deleteAccountOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (deleteAccountOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-account-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-account-title">Delete account?</h3>
            <p class="muted">This permanently deletes your account and all collections you own. This cannot be undone.</p>
            <div class="field"><label>Password<input type="password" bind:value={deletePassword} autocomplete="current-password" /></label></div>
            {#if totpStatus?.enabled}
                <div class="field"><label>Authenticator code<input bind:value={deleteTotpCode} maxlength={10} inputmode="numeric" placeholder="000000" /></label></div>
            {/if}
            {#if deleteMessage}<p class="error">{deleteMessage}</p>{/if}
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (deleteAccountOpen = false)}>Cancel</button>
                <button type="button" class="danger" onclick={deleteAccount}>Delete my account</button>
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

    .notif-table th, .notif-table td {
        padding: 0.4rem 0.6rem;
        text-align: left;
        font-size: 0.875rem;
    }
    .notif-table { border-collapse: collapse; width: 100%; }

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
    .notif-table thead tr { border-bottom: 1px solid var(--border); }

    .banner-warn {
        background: #fef3c7;
        border: 1px solid #f59e0b;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        color: #92400e;
    }
    [data-theme='dark'] .banner-warn {
        background: #451a03;
        border-color: #d97706;
        color: #fcd34d;
    }

    .settings-grid {
        display: grid;
        gap: 0.75rem;
    }
    .setting-row {
        display: grid;
        gap: 0.2rem;
        padding: 0.65rem 0.75rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: var(--surface-2);
    }
    .setting-meta {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .setting-key {
        font-weight: 600;
        font-size: 0.875rem;
        font-family: monospace;
    }
    .env-var {
        font-size: 0.75rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 4px;
        padding: 0.1rem 0.35rem;
        color: var(--muted);
    }
    .source-badge {
        font-size: 0.7rem;
        padding: 0.1rem 0.4rem;
        border-radius: 999px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .source-database { background: #dbeafe; color: #1e40af; }
    .source-environment { background: #d1fae5; color: #065f46; }
    .source-default { background: var(--surface); color: var(--muted); border: 1px solid var(--border); }
    [data-theme='dark'] .source-database { background: #1e3a5f; color: #93c5fd; }
    [data-theme='dark'] .source-environment { background: #064e3b; color: #6ee7b7; }
    .setting-desc { margin: 0; font-size: 0.8rem; }
    .setting-input {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .setting-input input, .setting-input select { flex: 1; min-width: 0; }
    button.small { padding: 0.25rem 0.6rem; font-size: 0.8rem; }

    .sensitive-wrap {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        flex: 1;
        min-width: 0;
    }
    .sensitive-wrap input { flex: 1; min-width: 0; }
    .set-badge {
        flex-shrink: 0;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 0.15rem 0.45rem;
        border-radius: 999px;
        background: #d1fae5;
        color: #065f46;
        border: 1px solid #6ee7b7;
        white-space: nowrap;
    }
    [data-theme='dark'] .set-badge {
        background: #064e3b;
        color: #6ee7b7;
        border-color: #065f46;
    }
</style>
