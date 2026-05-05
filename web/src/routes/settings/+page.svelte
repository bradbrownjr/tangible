<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, type SiteSetting } from '$lib/api';
    import { me, refreshMe } from '$lib/session';
    import { theme, palette, PALETTES, type ThemeMode } from '$lib/theme';
    import { _, locale } from 'svelte-i18n';
    import { LOCALES, setLocale } from '$lib/i18n';

    interface Token {
        id: string;
        name: string;
        token: string | null;
        last_used_at: string | null;
        expires_at: string | null;
        created_at: string;
    }

    interface NotificationPref {
        kind: string;
        email_enabled: boolean;
        push_enabled: boolean;
        browser_enabled: boolean;
        lead_days: number;
    }

    const KIND_LABELS = $derived<Record<string, string>>({
        maintenance_due: $_('settings.kind_maintenance_due'),
        chore_due: $_('settings.kind_chore_due'),
        item_use_by: $_('settings.kind_item_use_by'),
        item_expires: $_('settings.kind_item_expires'),
        lot_use_by: $_('settings.kind_lot_use_by'),
        low_stock: $_('settings.kind_low_stock'),
    });

    let tokens = $state<Token[]>([]);
    let notifPrefs = $state<NotificationPref[]>([]);;
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
    let testResults = $state<Record<string, { status: 'idle' | 'testing' | 'ok' | 'error'; message: string }>>({});
    const TESTABLE_INTEGRATION_KEYS = new Set(['discogs_token', 'tmdb_api_key', 'igdb_client_id', 'google_books_api_key', 'upcitemdb_key']);

    // Barcode adapter status
    let barcodeAdapters = $state<string[]>([]);
    const BARCODE_ADAPTER_INFO: Record<string, { label: string; description: string; keyHint?: string }> = {
        openlibrary:   { label: 'Open Library',    description: 'ISBN-10/13 lookup for books. Free, no API key required.' },
        musicbrainz:   { label: 'MusicBrainz',     description: 'Barcode lookup for music releases. Free; set TANGIBLE_MUSICBRAINZ_USER_AGENT for best results.' },
        openfoodfacts: { label: 'Open Food Facts', description: 'UPC/EAN lookup for food products. Free, no API key required.' },
        googlebooksapi:{ label: 'Google Books',    description: 'ISBN lookup via Google Books API.', keyHint: 'TANGIBLE_GOOGLE_BOOKS_API_KEY' },
        upcitemdb:     { label: 'UPCitemdb',       description: 'General product barcode lookup.', keyHint: 'TANGIBLE_UPCITEMDB_KEY' },
        discogs:       { label: 'Discogs',         description: 'Vinyl / music release lookup.', keyHint: 'TANGIBLE_DISCOGS_TOKEN' },
        tmdb:          { label: 'TMDB',            description: 'Movie and TV barcode lookup.', keyHint: 'TANGIBLE_TMDB_API_KEY' },
        igdb:          { label: 'IGDB',            description: 'Video game barcode lookup.', keyHint: 'TANGIBLE_IGDB_CLIENT_ID + TANGIBLE_IGDB_CLIENT_SECRET' },
    };
    async function loadBarcodeAdapters() {
        try {
            const r = await api.get<{ url: string[]; barcode: string[] }>('/metadata/adapters');
            barcodeAdapters = r.barcode;
        } catch { barcodeAdapters = []; }
    }

    // Enrollment enforcement
    const enrollRequired = $derived(!!$me?.enrollment_required);
    const enrollParam = $derived(page.url.searchParams.has('enroll'));

    // Tab + locale
    let activeTab = $state<'user' | 'admin'>('user');
    let selectedLocale = $state($me?.locale ?? $locale ?? 'en');
    $effect(() => { if ($me?.locale) selectedLocale = $me.locale; });

    async function changeLocale(code: string) {
        selectedLocale = code;
        setLocale(code);
        try {
            await api.patch('/auth/me', { locale: code });
            await refreshMe();
        } catch { /* non-fatal */ }
    }

    async function load() {
        try {
            [tokens, notifPrefs] = await Promise.all([
                api.get<Token[]>('/auth/tokens'),
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

    async function testEmail() {
        testResults['__email__'] = { status: 'testing', message: '' };
        try {
            const res = await api.post<{ ok: boolean; message: string }>('/admin/system/test-email', {});
            testResults['__email__'] = { status: res.ok ? 'ok' : 'error', message: res.message };
        } catch (e) {
            testResults['__email__'] = { status: 'error', message: (e as Error).message };
        }
    }

    async function testIntegration(key: string) {
        testResults[key] = { status: 'testing', message: '' };
        try {
            const res = await api.post<{ ok: boolean; message: string }>(`/admin/system/test-integration/${encodeURIComponent(key)}`, {});
            testResults[key] = { status: res.ok ? 'ok' : 'error', message: res.message };
        } catch (e) {
            testResults[key] = { status: 'error', message: (e as Error).message };
        }
    }

    // Group settings by section for display
    const SECTION_LABELS = $derived<Record<string, string>>({
        security: $_('settings.section_security'),
        sessions: $_('settings.section_sessions'),
        integrations: $_('settings.section_integrations'),
        email: $_('settings.section_email'),
    });

    onMount(async () => {
        await refreshMe();
        const promises: Promise<unknown>[] = [load(), loadTotpStatus()];
        if ($me?.is_admin) promises.push(loadSiteSettings(), loadBarcodeAdapters());
        await Promise.all(promises);
        // Auto-open 2FA setup when enrollment is required or ?enroll param is set
        if ((enrollRequired || enrollParam) && !totpStatus?.enabled && !totpSetup) {
            await startTotpSetup();
        }
    });
</script>

<h1>{$_('settings.title')}</h1>

{#if enrollRequired || enrollParam}
    <div class="banner-warn" role="alert">
        <strong>{$_('settings.enrollment_required_banner')}</strong>
        {$_('settings.enrollment_banner_message')}
    </div>
{/if}

{#if error}<p class="error">{error}</p>{/if}
{#if scrubResult}<p class="ok">{scrubResult}</p>{/if}

{#if $me?.is_admin}
    <div class="tab-bar" role="tablist">
        <button role="tab" class={activeTab === 'user' ? 'tab active' : 'tab'} aria-selected={activeTab === 'user'} onclick={() => (activeTab = 'user')}>{$_('settings.tab_user')}</button>
        <button role="tab" class={activeTab === 'admin' ? 'tab active' : 'tab'} aria-selected={activeTab === 'admin'} onclick={() => (activeTab = 'admin')}>{$_('settings.tab_admin')}</button>
    </div>
{/if}

{#if !$me?.is_admin || activeTab === 'user'}
<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">{$_('settings.appearance_heading')}</h3>
    <p class="muted">{$_('settings.appearance_description')}</p>

    <!-- Mode toggle (only relevant for palettes with mode='both') -->
    {#if PALETTES.find(p => p.id === $palette)?.mode === 'both'}
        <div role="radiogroup" aria-label="Theme mode" class="theme-toggle" style="margin-bottom:1rem">
            {#each ['light', 'dark', 'system'] as const as opt (opt)}
                <button
                    type="button"
                    class={$theme === opt ? '' : 'secondary'}
                    aria-pressed={$theme === opt}
                    onclick={() => theme.set(opt as ThemeMode)}
                >
                    {opt === 'light' ? $_('settings.theme_light') : opt === 'dark' ? $_('settings.theme_dark') : $_('settings.theme_system')}
                </button>
            {/each}
        </div>
    {/if}

    <!-- Palette grid -->
    <p style="font-size:var(--text-sm);color:var(--text-muted);margin:0 0 0.5rem">{$_('settings.palette_label')}</p>
    <div class="palette-grid">
        {#each PALETTES as p (p.id)}
            <button
                type="button"
                class="palette-card {$palette === p.id ? 'palette-card--active' : 'secondary'}"
                onclick={() => palette.set(p.id)}
                aria-pressed={$palette === p.id}
                title={p.name}
            >
                <span class="palette-swatch" style="background:{p.bg}">
                    <span class="palette-accent" style="background:{p.accent}"></span>
                </span>
                <span class="palette-name">{p.name}</span>
            </button>
        {/each}
    </div>

    <div style="margin-top:0.75rem">
        <label for="lang-select" style="display:block;margin-bottom:0.35rem;font-size:0.875rem">{$_('settings.language_label')}</label>
        <select
            id="lang-select"
            value={selectedLocale}
            onchange={(e) => changeLocale((e.target as HTMLSelectElement).value)}
            style="width:auto"
        >
            {#each LOCALES as loc (loc.code)}
                <option value={loc.code}>{loc.label}</option>
            {/each}
        </select>
    </div>
</div>

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">{$_('settings.notifications_heading')}</h3>
    <p class="muted">{$_('settings.notifications_description')}</p>
    {#if notifPrefs.length > 0}
        <table class="notif-table">
            <thead>
                <tr>
                    <th>{$_('settings.notif_col_type')}</th>
                    <th title={$_('settings.notif_col_email')}>{$_('settings.notif_col_email')}</th>
                    <th title="Browser notification when the app is open">{$_('settings.notif_col_browser')}</th>
                    <th title="Daily notification on the Android app">{$_('settings.notif_col_app')}</th>
                    <th>{$_('settings.notif_col_lead')}</th>
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
        <button onclick={sendDigest}>{$_('settings.send_digest_button')}</button>
        <button class="secondary" onclick={requestBrowserPermission}>{$_('settings.browser_permission_button')}</button>
        {#if digestMessage}
            <span class={digestQueued ? 'ok' : 'muted'}>{digestMessage}</span>
        {/if}
    </div>
</div>

<div class="card">
    <h3 style="margin-top:0">{$_('settings.api_tokens_heading')}</h3>
    <p class="muted">{$_('settings.api_tokens_description')}</p>

    <form onsubmit={create} style="display:flex; gap:.5rem; margin-bottom:1rem">
        <input bind:value={newName} placeholder={$_('settings.token_name_placeholder')} />
        <button type="submit">{$_('settings.create_token_button')}</button>
    </form>

    {#if issuedRaw}
        <div class="card" style="background: var(--surface-2); margin-bottom: 1rem">
            <p>
                <strong>{$_('settings.token_save_message')}</strong>
            </p>
            <pre style="word-break: break-all; white-space: pre-wrap">{issuedRaw}</pre>
            <button class="secondary" onclick={() => (issuedRaw = '')}>{$_('settings.token_dismiss_button')}</button>
        </div>
    {/if}

    {#if tokens.length === 0}
        <p class="muted">{$_('settings.no_tokens')}</p>
    {:else}
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
                            <button class="danger" onclick={() => (revokeModalTokenId = t.id)}>{$_('settings.token_revoke_button')}</button>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
</div>

<div class="card" style="margin-bottom: 1rem">
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
        <img src="data:image/png;base64,{totpSetup.qr_png_b64}" alt="TOTP QR code" style="display:block; margin: 0.75rem 0; max-width:200px; image-rendering:pixelated" />
        <p class="muted">{$_('settings.totp_secret_label')} <code>{totpSetup.secret}</code></p>
        <div style="display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap">
            <input bind:value={totpSetupCode} placeholder={$_('settings.totp_code_placeholder')} maxlength={6} inputmode="numeric" autocomplete="one-time-code" style="width:9rem" />
            <button onclick={verifyTotpSetup}>{$_('settings.totp_activate_button')}</button>
            <button class="secondary" onclick={() => { totpSetup = null; totpSetupCode = ''; }}>{$_('common.cancel')}</button>
        </div>
        {#if totpSetupMessage}<p class="error">{totpSetupMessage}</p>{/if}
    {:else}
        <p class="muted">{$_('settings.totp_disabled_message')}</p>
        <button onclick={startTotpSetup}>{$_('settings.totp_setup_button')}</button>
        {#if totpSetupMessage}<p class="error">{totpSetupMessage}</p>{/if}
    {/if}
</div>

<div class="card" style="margin-bottom: 1rem">
    <h3 style="margin-top:0">{$_('settings.account_heading')}</h3>
    <p class="muted">{$_('settings.account_description')}</p>
    <div style="display:flex; gap:0.5rem; flex-wrap:wrap">
        <button class="secondary" onclick={exportAccount}>{$_('settings.export_data_button')}</button>
        <button class="danger" onclick={() => (deleteAccountOpen = true)}>{$_('settings.delete_account_button')}</button>
    </div>
</div>

{/if}

{#if $me?.is_admin && activeTab === 'admin'}
    {#if siteSettingsLoaded}
        <div class="card" style="margin-top: 1rem">
            <h3 style="margin-top:0">{$_('settings.server_settings_heading')}</h3>
            <p class="muted">
                {$_('settings.server_settings_description')}
                <span class="muted" style="font-size:0.8rem">{$_('settings.server_settings_env_note')}</span>
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
                                                <span class="set-badge" title={$_('settings.setting_sensitive_title')}>{$_('settings.setting_sensitive_set_badge')}</span>
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
                                        <button class="secondary small" title={$_('settings.setting_revert_title')} onclick={() => clearSiteSetting(s.key)}>{$_('settings.setting_revert_button')}</button>
                                    {/if}
                                    {#if TESTABLE_INTEGRATION_KEYS.has(s.key)}
                                        <button class="secondary small" disabled={testResults[s.key]?.status === 'testing'} onclick={() => testIntegration(s.key)}>
                                            {testResults[s.key]?.status === 'testing' ? $_('settings.testing_button') : $_('settings.test_connection_button')}
                                        </button>
                                        {#if testResults[s.key]?.status === 'ok'}<span class="ok" style="font-size:0.8rem">&#10003; {testResults[s.key].message}</span>{/if}
                                        {#if testResults[s.key]?.status === 'error'}<span class="error" style="font-size:0.8rem">&#10007; {testResults[s.key].message}</span>{/if}
                                    {/if}
                                </div>
                            </div>
                        {/each}
                    </div>
                    {#if section === 'email'}
                        <div style="margin-top:0.75rem;display:flex;align-items:center;gap:0.75rem;flex-wrap:wrap">
                            <button class="secondary small" disabled={testResults['__email__']?.status === 'testing'} onclick={testEmail}>
                                {testResults['__email__']?.status === 'testing' ? $_('settings.testing_button') : $_('settings.test_email_button')}
                            </button>
                            {#if testResults['__email__']?.status === 'ok'}<span class="ok" style="font-size:0.85rem">&#10003; {testResults['__email__'].message}</span>{/if}
                            {#if testResults['__email__']?.status === 'error'}<span class="error" style="font-size:0.85rem">&#10007; {testResults['__email__'].message}</span>{/if}
                        </div>
                    {/if}
                {/if}
            {/each}
            {#if siteSettingsError}<p class="error">{siteSettingsError}</p>{/if}
            {#if siteSettingsSaved}<p class="ok">{$_('settings.settings_saved_message')}</p>{/if}
            <div style="margin-top:1rem;display:flex;gap:0.5rem">
                <button onclick={saveSiteSettings}>{$_('settings.save_settings_button')}</button>
                <button class="secondary" onclick={loadSiteSettings}>{$_('settings.reset_settings_button')}</button>
            </div>
        </div>
    {/if}
    <div class="card" style="margin-top: 1rem">
        <h3 style="margin-top:0">Barcode &amp; Metadata Services</h3>
        <p class="muted">
            These services are tried in order when a barcode is scanned. Built-in free services require no configuration.
            Optional services marked with a key icon enhance coverage for specific categories.
        </p>
        {#if barcodeAdapters.length === 0}
            <p class="muted">No barcode adapters loaded.</p>
        {:else}
            <table style="width:100%;border-collapse:collapse;font-size:0.9rem">
                <thead>
                    <tr style="text-align:left;border-bottom:1px solid var(--border)">
                        <th style="padding:0.4rem 0.5rem">Service</th>
                        <th style="padding:0.4rem 0.5rem">Covers</th>
                        <th style="padding:0.4rem 0.5rem">API key env var</th>
                    </tr>
                </thead>
                <tbody>
                    {#each barcodeAdapters as name}
                        {@const info = BARCODE_ADAPTER_INFO[name]}
                        <tr style="border-bottom:1px solid var(--border)">
                            <td style="padding:0.4rem 0.5rem;font-weight:500">{info?.label ?? name}</td>
                            <td style="padding:0.4rem 0.5rem;color:var(--muted)">{info?.description ?? ''}</td>
                            <td style="padding:0.4rem 0.5rem">
                                {#if info?.keyHint}
                                    <code style="font-size:0.8rem">{info.keyHint}</code>
                                {:else}
                                    <span class="muted">not required</span>
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}
        <p class="muted" style="margin-top:0.75rem;font-size:0.85rem">
            Add optional API keys in the <strong>Integrations</strong> section of Server Settings above, or via environment variables on the server.
            See <a href="https://github.com/bradbrownjr/tangible/blob/main/docs/admin-guide.md" target="_blank" rel="noopener">admin guide</a> for details.
        </p>
    </div>
    <div class="card" style="margin-top: 1rem">
        <h3 style="margin-top:0">{$_('settings.system_maintenance_heading')}</h3>
        <p class="muted">
            {$_('settings.system_maintenance_description')}
        </p>
        <button class="danger" type="button" onclick={() => (scrubModalOpen = true)}>{$_('settings.scrub_inventory_button')}</button>
    </div>
{/if}

{#if revokeModalTokenId}
    <div class="modal-backdrop" role="presentation" onclick={() => (revokeModalTokenId = null)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="revoke-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="revoke-title">{$_('settings.revoke_token_title')}</h3>
            <p class="muted">{$_('settings.revoke_token_text')}</p>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (revokeModalTokenId = null)}>{$_('common.cancel')}</button>
                <button type="button" class="danger" onclick={revokeConfirmed}>{$_('settings.revoke_token_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

{#if scrubModalOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (scrubModalOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="scrub-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="scrub-title">{$_('settings.scrub_title')}</h3>
            <p class="muted">
                {$_('settings.scrub_text')}
            </p>
            <label for="scrub-confirm" class="muted">{$_('settings.scrub_confirm_label', { values: { phrase: scrubPhrase } })}</label>
            <input id="scrub-confirm" bind:value={scrubConfirmText} placeholder={scrubPhrase} />
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (scrubModalOpen = false)}>{$_('common.cancel')}</button>
                <button
                    type="button"
                    class="danger"
                    disabled={scrubConfirmText.trim().toUpperCase() !== scrubPhrase}
                    onclick={scrubInventory}
                >{$_('settings.scrub_confirm_button')}</button>
            </div>
        </div>
    </div>
{/if}

{#if totpDisableOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (totpDisableOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="totp-disable-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="totp-disable-title">{$_('settings.totp_disable_title')}</h3>
            <p class="muted">{$_('settings.totp_disable_text')}</p>
            <div class="field"><label>{$_('settings.totp_disable_password_label')}<input type="password" bind:value={totpDisablePassword} autocomplete="current-password" /></label></div>
            <div class="field"><label>{$_('settings.totp_disable_code_label')}<input bind:value={totpDisableCode} maxlength={10} inputmode="numeric" placeholder={$_('settings.totp_disable_code_placeholder')} /></label></div>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (totpDisableOpen = false)}>{$_('common.cancel')}</button>
                <button type="button" class="danger" onclick={disableTotp}>{$_('settings.totp_disable_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

{#if totpRegenOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (totpRegenOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="totp-regen-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="totp-regen-title">{$_('settings.totp_regen_title')}</h3>
            <p class="muted">{$_('settings.totp_regen_text')}</p>
            <div class="field"><label>{$_('settings.totp_disable_code_label')}<input bind:value={totpRegenCode} maxlength={10} inputmode="numeric" placeholder={$_('settings.totp_regen_code_placeholder')} /></label></div>
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (totpRegenOpen = false)}>{$_('common.cancel')}</button>
                <button type="button" onclick={regenBackupCodes}>{$_('settings.totp_regen_confirm')}</button>
            </div>
        </div>
    </div>
{/if}

{#if deleteAccountOpen}
    <div class="modal-backdrop" role="presentation" onclick={() => (deleteAccountOpen = false)}>
        <div class="modal" role="dialog" aria-modal="true" aria-labelledby="delete-account-title" onclick={(e) => e.stopPropagation()}>
            <h3 id="delete-account-title">{$_('settings.delete_account_title')}</h3>
            <p class="muted">{$_('settings.delete_account_text')}</p>
            <div class="field"><label>{$_('settings.totp_disable_password_label')}<input type="password" bind:value={deletePassword} autocomplete="current-password" /></label></div>
            {#if totpStatus?.enabled}
                <div class="field"><label>{$_('settings.totp_disable_code_label')}<input bind:value={deleteTotpCode} maxlength={10} inputmode="numeric" placeholder={$_('settings.delete_totp_placeholder')} /></label></div>
            {/if}
            {#if deleteMessage}<p class="error">{deleteMessage}</p>{/if}
            <div class="modal-actions">
                <button type="button" class="secondary" onclick={() => (deleteAccountOpen = false)}>{$_('common.cancel')}</button>
                <button type="button" class="danger" onclick={deleteAccount}>{$_('settings.delete_confirm_button')}</button>
            </div>
        </div>
    </div>
{/if}

<style>
    .tab-bar {
        display: flex;
        gap: 0;
        border-bottom: 2px solid var(--border);
        margin-bottom: 1.25rem;
    }
    .tab {
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        padding: 0.5rem 1.25rem;
        font-size: 0.95rem;
        cursor: pointer;
        color: var(--muted);
        border-radius: 0;
    }
    .tab.active {
        color: var(--text);
        border-bottom-color: var(--accent);
        font-weight: 600;
    }
    .tab:hover:not(.active) {
        color: var(--text);
        background: color-mix(in srgb, var(--text) 5%, transparent);
    }

    .theme-toggle {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .palette-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
        gap: 0.5rem;
    }

    .palette-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.35rem;
        padding: 0.5rem;
        background: var(--surface-2);
        border: 2px solid transparent;
        border-radius: var(--radius-md);
        cursor: pointer;
        min-height: auto;
        transition: border-color 0.15s;
    }
    .palette-card--active {
        border-color: var(--accent);
    }

    .palette-swatch {
        width: 48px;
        height: 32px;
        border-radius: var(--radius-sm);
        border: 1px solid rgba(0,0,0,0.12);
        display: flex;
        align-items: flex-end;
        justify-content: flex-end;
        padding: 4px;
        position: relative;
    }

    .palette-accent {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 1.5px solid rgba(255,255,255,0.5);
    }

    .palette-name {
        font-size: var(--text-xs);
        color: var(--text-muted);
        text-align: center;
        line-height: 1.2;
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
