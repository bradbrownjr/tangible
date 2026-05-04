<script lang="ts">
    import '$lib/styles.css';
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { me, refreshMe, loadPublicConfig, logout, publicConfig } from '$lib/session';
    import { userLabel, api, type Collection } from '$lib/api';
    import { get } from 'svelte/store';
    import { initTheme } from '$lib/theme';
    import { _, locale } from 'svelte-i18n';
    import { initI18n } from '$lib/i18n';
    import WhatsNew from '$lib/WhatsNew.svelte';
    import AlertsDropdown from '$lib/AlertsDropdown.svelte';

    // Initialise i18n synchronously so strings are ready before first render.
    initI18n();

    const SEEN_KEY = 'tangible:whatsnew-seen-version';
    const BROWSER_NOTIF_KEY = 'tangible:browser-notif-fired';

    interface NotificationPref { kind: string; browser_enabled: boolean; lead_days: number; }
    interface DueAlert { id: string; title: string; details: string | null; due_at: string; kind: string; severity: string; }
    interface ShoppingCount { total: number; ad_hoc: number; depleted_items: number; by_type: Record<string, number>; }

    let { children } = $props();
    let ready = $state(false);
    let whatsNewOpen = $state(false);
    let lastSeen = $state<string | null>(null);
    let shoppingCount = $state(0);
    let shoppingByType = $state<Record<string, number>>({});
    let listsMenuOpen = $state(false);
    let collectionsMenuOpen = $state(false);
    let navCollections = $state<Collection[]>([]);
    let menuOpen = $state(false);

    async function refreshNavCollections() {
        if (!$me) { navCollections = []; return; }
        try {
            navCollections = await api.get<Collection[]>('/collections');
        } catch {
            navCollections = [];
        }
    }

    async function refreshShoppingCount() {
        if (!$me) { shoppingCount = 0; shoppingByType = {}; return; }
        try {
            const c = await api.get<ShoppingCount>("/lists/count");
            shoppingCount = c.total;
            shoppingByType = c.by_type ?? {};
        } catch {
            shoppingCount = 0;
            shoppingByType = {};
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
        await Promise.all([refreshShoppingCount(), refreshNavCollections()]);
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

    function closeMenu() { menuOpen = false; listsMenuOpen = false; collectionsMenuOpen = false; }

    function handleDocumentClick() { listsMenuOpen = false; collectionsMenuOpen = false; }

    $effect(() => {
        document.documentElement.lang = $locale ?? 'en';
    });
</script>

<svelte:document onclick={handleDocumentClick} />

<header>
    <a href="/" class="brand">Tangible</a>
    {#if $publicConfig?.version}<span class="version muted">v{$publicConfig.version}</span>{/if}
    <button
        class="icon-btn whats-new"
        onclick={openWhatsNew}
        title={$_('nav.whats_new')}
        aria-label={$_('nav.whats_new')}
    >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
                fill="currentColor"
                d="M12 2a1 1 0 0 1 .894.553l1.382 2.764 3.05.443a1 1 0 0 1 .554 1.706l-2.207 2.151.521 3.038a1 1 0 0 1-1.451 1.054L12 12.347l-2.743 1.362a1 1 0 0 1-1.451-1.054l.521-3.038-2.207-2.151a1 1 0 0 1 .554-1.706l3.05-.443 1.382-2.764A1 1 0 0 1 12 2zm6 14a1 1 0 0 1 .894.553l.553 1.106 1.106.553a1 1 0 0 1 0 1.788l-1.106.553-.553 1.106a1 1 0 0 1-1.788 0l-.553-1.106-1.106-.553a1 1 0 0 1 0-1.788l1.106-.553.553-1.106A1 1 0 0 1 18 16zM5 13a1 1 0 0 1 .894.553l.553 1.106 1.106.553a1 1 0 0 1 0 1.788l-1.106.553-.553 1.106a1 1 0 0 1-1.788 0l-.553-1.106-1.106-.553a1 1 0 0 1 0-1.788l1.106-.553.553-1.106A1 1 0 0 1 5 13z"
            />
        </svg>
        {#if hasUnseen}<span class="dot" aria-hidden="true"></span>{/if}
    </button>
    <span class="header-spacer"></span>
    {#if $me}<AlertsDropdown />{/if}
    {#if $me}
        <button
            class="icon-btn hamburger"
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
            onclick={() => (menuOpen = !menuOpen)}
        >
            <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                {#if menuOpen}
                    <path fill="currentColor" d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                {:else}
                    <path fill="currentColor" d="M3 6h18M3 12h18M3 18h18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                {/if}
            </svg>
        </button>
    {/if}
    <nav class:open={menuOpen}>
        {#if $me}
            <div class="nav-lists-menu" class:open={collectionsMenuOpen}>
                    <button
                        class="nav-lists-trigger"
                        onclick={(e) => { e.stopPropagation(); collectionsMenuOpen = !collectionsMenuOpen; listsMenuOpen = false; }}
                        aria-haspopup="true"
                        aria-expanded={collectionsMenuOpen}
                    >
                        {$_('nav.collections')}
                        <svg class="chevron" viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                            <path fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6"/>
                        </svg>
                    </button>
                    {#if collectionsMenuOpen}
                        <div class="nav-lists-dropdown" role="menu">
                            <a href="/" role="menuitem" onclick={() => { collectionsMenuOpen = false; closeMenu(); }}>
                                {$_('nav.all_collections')}
                            </a>
                            {#each navCollections as col}
                                <a href="/collections/{col.id}" role="menuitem" onclick={() => { collectionsMenuOpen = false; closeMenu(); }}>
                                    {col.name}
                                </a>
                            {/each}
                            <a href="/?new=1" role="menuitem" class="add-collection-link" onclick={() => { collectionsMenuOpen = false; closeMenu(); }}>
                                {$_('collections.add_button')}
                            </a>
                        </div>
                    {/if}
                </div>
            <div class="nav-lists-menu" class:open={listsMenuOpen}>
                <button
                    class="nav-lists-trigger"
                    onclick={(e) => { e.stopPropagation(); listsMenuOpen = !listsMenuOpen; collectionsMenuOpen = false; }}
                    aria-haspopup="true"
                    aria-expanded={listsMenuOpen}
                >
                    {$_('nav.lists')}{#if shoppingCount > 0} <span class="badge">{shoppingCount}</span>{/if}
                    <svg class="chevron" viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                        <path fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6"/>
                    </svg>
                </button>
                {#if listsMenuOpen}
                    <div class="nav-lists-dropdown" role="menu">
                        <a href="/lists/groceries" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.groceries')}{#if (shoppingByType['groceries'] ?? 0) > 0} <span class="badge">{shoppingByType['groceries']}</span>{/if}
                        </a>
                        <a href="/lists/hardware" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.hardware')}{#if (shoppingByType['hardware'] ?? 0) > 0} <span class="badge">{shoppingByType['hardware']}</span>{/if}
                        </a>
                        <a href="/lists/home_goods" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.home_goods')}{#if (shoppingByType['home_goods'] ?? 0) > 0} <span class="badge">{shoppingByType['home_goods']}</span>{/if}
                        </a>
                        <a href="/lists/wish_list" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.wish_list')}{#if (shoppingByType['wish_list'] ?? 0) > 0} <span class="badge">{shoppingByType['wish_list']}</span>{/if}
                        </a>
                    </div>
                {/if}
            </div>
            <a href="/maintenance" onclick={closeMenu}>{$_('nav.maintenance')}</a>
            <a href="/settings" onclick={closeMenu}>{$_('nav.settings')}</a>
            <a href="/profile" class="user" onclick={closeMenu} title={$_('nav.edit_profile')}>{userLabel($me)}</a>
            <button class="secondary" onclick={doLogout}>{$_('nav.log_out')}</button>
        {/if}
    </nav>
</header>

<main>
    {#if ready}
        {@render children()}
    {:else}
        <p class="muted">{$_('common.loading')}</p>
    {/if}
</main>

{#if whatsNewOpen}
    <WhatsNew onClose={closeWhatsNew} />
{/if}

<style>
    header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1.5rem;
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        flex-wrap: wrap;
        position: relative;
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
    /* spacer pushes bell + hamburger to the right on all screen sizes */
    .header-spacer {
        flex: 1;
    }
    /* hamburger: hidden on desktop, shown on mobile */
    .hamburger {
        display: none;
    }
    nav {
        display: flex;
        gap: 1rem;
        align-items: center;
    }
    nav a {
        color: var(--text);
        font-size: 1rem;
        text-decoration: none;
    }
    nav a:hover {
        color: var(--accent);
    }
    /* Lists dropdown */
    .nav-lists-menu {
        position: relative;
    }
    .nav-lists-trigger {
        background: none;
        border: none;
        color: var(--text);
        font-size: 1rem;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        padding: 0;
    }
    .nav-lists-trigger:hover {
        color: var(--accent);
    }
    .chevron {
        transition: transform 0.15s;
    }
    .nav-lists-menu.open .chevron {
        transform: rotate(180deg);
    }
    .nav-lists-dropdown {
        position: absolute;
        top: calc(100% + 0.5rem);
        left: 0;
        min-width: 160px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 0.5rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12);
        z-index: 200;
        display: flex;
        flex-direction: column;
        overflow: hidden;
    }
    .nav-lists-dropdown a {
        padding: 0.6rem 1rem;
        color: var(--text);
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .nav-lists-dropdown a:hover {
        background: color-mix(in srgb, var(--accent) 10%, transparent);
        color: var(--accent);
    }
    .nav-lists-dropdown .add-collection-link {
        border-top: 1px solid var(--border);
        color: var(--accent);
        font-size: 0.9rem;
    }
    main {
        padding: 1.5rem;
        max-width: 1100px;
        margin: 0 auto;
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
    /* --- responsive nav --- */
    @media (max-width: 768px) {
        .hamburger {
            display: inline-flex;
        }
        /* hide the whats-new button text label on very small screens */
        nav {
            display: none;
            width: 100%;
            flex-direction: column;
            align-items: flex-start;
            gap: 0;
            margin-left: 0;
            padding: 0.5rem 0;
            border-top: 1px solid var(--border);
        }
        nav.open {
            display: flex;
        }
        nav a,
        nav :global(button) {
            width: 100%;
            padding: 0.65rem 0.5rem;
            border-radius: 0;
            font-size: 1rem;
            text-align: left;
        }
        nav a:hover {
            background: color-mix(in srgb, var(--text) 6%, transparent);
        }
        .nav-lists-trigger {
            width: 100%;
            padding: 0.65rem 0.5rem;
            border-radius: 0;
            text-align: left;
        }
        .nav-lists-dropdown {
            position: static;
            box-shadow: none;
            border: none;
            border-radius: 0;
            border-left: 2px solid var(--accent);
            margin-left: 0.75rem;
        }
        .nav-lists-dropdown a {
            padding: 0.5rem 0.75rem;
        }
    }
</style>
