<script lang="ts">
    import '$lib/styles.css';
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { me, refreshMe, loadPublicConfig, logout, publicConfig } from '$lib/session';
    import { userLabel, api } from '$lib/api';
    import { get } from 'svelte/store';
    import { initTheme } from '$lib/theme';
    import { _, locale } from 'svelte-i18n';
    import { initI18n, setLocale, LOCALES } from '$lib/i18n';
    import WhatsNew from '$lib/WhatsNew.svelte';

    // Initialise i18n synchronously so strings are ready before first render.
    initI18n();

    const SEEN_KEY = 'tangible:whatsnew-seen-version';
    const BROWSER_NOTIF_KEY = 'tangible:browser-notif-fired';

    interface NotificationPref { kind: string; browser_enabled: boolean; lead_days: number; }
    interface DueAlert { id: string; title: string; details: string | null; due_at: string; kind: string; severity: string; }
    interface GroceryCount { total: number; ad_hoc: number; depleted_items: number; }

    let { children } = $props();
    let ready = $state(false);
    let whatsNewOpen = $state(false);
    let lastSeen = $state<string | null>(null);
    let groceryCount = $state(0);

    async function refreshGroceryCount() {
        if (!$me) { groceryCount = 0; return; }
        try {
            const c = await api.get<GroceryCount>('/grocery/count');
            groceryCount = c.total;
        } catch {
            groceryCount = 0;
        }
    }

    const hasUnseen = $derived(
        !!$publicConfig?.version && lastSeen !== $publicConfig.version
    );

    function openWhatsNew() {
        whatsNewOpen = true;
        if ($publicConfig?.version) {
            try {
                localStorage.setItem(SEEN_KEY, $publicConfig.version);
                lastSeen = $publicConfig.version;
            } catch {
                // localStorage may be disabled; non-fatal.
            }
        }
    }

    function closeWhatsNew() {
        whatsNewOpen = false;
    }

    onMount(async () => {
        initTheme();
        try {
            lastSeen = localStorage.getItem(SEEN_KEY);
        } catch {
            lastSeen = null;
        }
        await Promise.all([refreshMe(), loadPublicConfig()]);
        ready = true;
        await refreshGroceryCount();
        const path = page.url.pathname;
        const onAuth = path === '/login' || path === '/register';
        const isPublic = path.startsWith('/share/') || path.startsWith('/invite/');
        if (!$me && !onAuth && !isPublic) {
            const cfg = get(publicConfig);
            await goto(cfg?.setup_required ? '/register' : '/login');
        } else if ($me && onAuth) {
            await goto('/');
        } else if ($me?.enrollment_required && path !== '/settings') {
            await goto('/settings?enroll=1');
        }

        // Browser push notifications: fire once per session for browser_enabled kinds.
        if ($me && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            try {
                const todayKey = new Date().toISOString().slice(0, 10);
                const fired = localStorage.getItem(BROWSER_NOTIF_KEY);
                if (fired !== todayKey) {
                    const [prefs, alerts] = await Promise.all([
                        api.get<NotificationPref[]>('/notifications'),
                        api.get<DueAlert[]>('/alerts?within_days=30'),
                    ]);
                    const enabledKinds = new Set(
                        prefs.filter(p => p.browser_enabled).map(p => p.kind)
                    );
                    const kindLeadDays = Object.fromEntries(prefs.map(p => [p.kind, p.lead_days]));
                    const now = Date.now();
                    for (const alert of alerts) {
                        if (!enabledKinds.has(alert.kind)) continue;
                        const lead = (kindLeadDays[alert.kind] ?? 7) * 86400 * 1000;
                        const due = new Date(alert.due_at).getTime();
                        if (due - now <= lead) {
                            new Notification(alert.title, { body: alert.details ?? undefined, tag: alert.id });
                        }
                    }
                    localStorage.setItem(BROWSER_NOTIF_KEY, todayKey);
                }
            } catch {
                // Non-fatal: browser notification errors must never break the app shell.
            }
        }
    });

    async function doLogout() {
        await logout();
        await goto('/login');
    }

    $effect(() => {
        document.documentElement.lang = $locale ?? 'en';
    });
</script>

<header>
    <a href="/" class="brand">Tangible</a>
    {#if $publicConfig?.version}<span class="version muted">v{$publicConfig.version}</span>{/if}
    <button
        class="icon-btn whats-new"
        onclick={openWhatsNew}
        title="What's new"
        aria-label="What's new"
    >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
                fill="currentColor"
                d="M12 2a1 1 0 0 1 .894.553l1.382 2.764 3.05.443a1 1 0 0 1 .554 1.706l-2.207 2.151.521 3.038a1 1 0 0 1-1.451 1.054L12 12.347l-2.743 1.362a1 1 0 0 1-1.451-1.054l.521-3.038-2.207-2.151a1 1 0 0 1 .554-1.706l3.05-.443 1.382-2.764A1 1 0 0 1 12 2zm6 14a1 1 0 0 1 .894.553l.553 1.106 1.106.553a1 1 0 0 1 0 1.788l-1.106.553-.553 1.106a1 1 0 0 1-1.788 0l-.553-1.106-1.106-.553a1 1 0 0 1 0-1.788l1.106-.553.553-1.106A1 1 0 0 1 18 16zM5 13a1 1 0 0 1 .894.553l.553 1.106 1.106.553a1 1 0 0 1 0 1.788l-1.106.553-.553 1.106a1 1 0 0 1-1.788 0l-.553-1.106-1.106-.553a1 1 0 0 1 0-1.788l1.106-.553.553-1.106A1 1 0 0 1 5 13z"
            />
        </svg>
        {#if hasUnseen}<span class="dot" aria-hidden="true"></span>{/if}
    </button>
    <nav>
        {#if $me}
            <a href="/">{$_('nav.collections')}</a>
            <a href="/maintenance">{$_('nav.maintenance')}</a>
            <a href="/grocery-list">{$_('nav.grocery_list')}{#if groceryCount > 0} <span class="badge">{groceryCount}</span>{/if}</a>
            <a href="/import">{$_('nav.import')}</a>
            <a href="/settings">{$_('nav.settings')}</a>
            <a href="/profile" class="user" title="Edit your profile">{userLabel($me)}</a>
            <button class="secondary" onclick={doLogout}>{$_('nav.log_out')}</button>
        {/if}
        <select
            class="locale-picker"
            value={$locale}
            onchange={(e) => setLocale((e.target as HTMLSelectElement).value)}
            aria-label={$_('lang.label')}
        >
            {#each LOCALES as loc}
                <option value={loc.code}>{loc.label}</option>
            {/each}
        </select>
    </nav>
</header>

<main>
    {#if ready}
        {@render children()}
    {:else}
        <p class="muted">Loading…</p>
    {/if}
</main>

{#if whatsNewOpen}
    <WhatsNew onClose={closeWhatsNew} />
{/if}

<style>
    header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 0.75rem 1.5rem;
        background: var(--surface);
        border-bottom: 1px solid var(--border);
    }
    .brand {
        font-weight: 700;
        font-size: 1.25rem;
        color: var(--text);
    }
    .version {
        font-size: 0.75rem;
    }
    .icon-btn {
        position: relative;
        background: transparent;
        border: none;
        color: var(--text);
        padding: 0.25rem;
        border-radius: 0.375rem;
        display: inline-flex;
        align-items: center;
        cursor: pointer;
    }
    .icon-btn:hover {
        background: color-mix(in srgb, var(--text) 8%, transparent);
    }
    .dot {
        position: absolute;
        top: 2px;
        right: 2px;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--accent);
        border: 2px solid var(--surface);
    }
    nav {
        display: flex;
        gap: 1rem;
        align-items: center;
        margin-left: auto;
    }
    nav a {
        color: var(--text);
        font-size: 1rem;
        text-decoration: none;
    }
    nav a:hover {
        color: var(--accent);
    }
    main {
        padding: 1.5rem;
        max-width: 1100px;
        margin: 0 auto;
    }
    .locale-picker {
        font-size: 0.8rem;
        padding: 0.2rem 0.4rem;
        border: 1px solid var(--border, #e5e7eb);
        border-radius: 4px;
        background: var(--surface);
        color: var(--text);
        cursor: pointer;
    }
    .badge {
        display: inline-block;
        min-width: 1.2em;
        padding: 0 0.4em;
        margin-left: 0.25em;
        font-size: 0.75rem;
        line-height: 1.4;
        text-align: center;
        border-radius: 999px;
        background: var(--accent, #2563eb);
        color: #fff;
    }
</style>
