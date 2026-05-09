<script lang="ts">
    import '$lib/styles.css';
    import { onMount } from 'svelte';
    import { goto, afterNavigate } from '$app/navigation';
    import { page } from '$app/state';
    import { me, refreshMe, loadPublicConfig, logout, publicConfig } from '$lib/session';
    import { userLabel, api, type Collection } from '$lib/api';
    import { get } from 'svelte/store';
    import { initTheme } from '$lib/theme';
    import { _, locale } from 'svelte-i18n';
    import { initI18n } from '$lib/i18n';
    import WhatsNew from '$lib/WhatsNew.svelte';
    import AlertsDropdown from '$lib/AlertsDropdown.svelte';
    import Toast from '$lib/Toast.svelte';
    import Icon from '$lib/Icon.svelte';

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
            navCollections = await api.get<Collection[]>('/collections', true);
        } catch {
            navCollections = [];
        }
    }

    async function refreshShoppingCount() {
        if (!$me) { shoppingCount = 0; shoppingByType = {}; return; }
        try {
            const c = await api.get<ShoppingCount>("/lists/count", true);
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
        } else if ($me?.enrollment_required && !path.startsWith('/settings')) {
            await goto('/settings/security?enroll=1');
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

    afterNavigate(() => { refreshNavCollections(); });

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
    <a href="/" class="brand">
        <img src="/icon-192.png" alt="" width="28" height="28" class="brand-logo" />
        <span>Tangible</span>
    </a>
    {#if $publicConfig?.version}<span class="version muted">v{$publicConfig.version}</span>{/if}
    <button
        class="icon-btn whats-new"
        onclick={openWhatsNew}
        title={$_('nav.whats_new')}
        aria-label={$_('nav.whats_new')}
    >
        <Icon name="sparkles" size={18} />
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
            <Icon name={menuOpen ? 'x' : 'menu'} size={22} />
        </button>
    {/if}
    <nav class:open={menuOpen}>
        {#if $me}
            <a href="/" class="nav-link" onclick={closeMenu}>
                <Icon name="home" size={16} />
                <span>{$_('nav.home')}</span>
            </a>
            <div class="nav-lists-menu" class:open={collectionsMenuOpen}>
                    <button
                        class="nav-lists-trigger"
                        onclick={(e) => { e.stopPropagation(); collectionsMenuOpen = !collectionsMenuOpen; listsMenuOpen = false; }}
                        aria-haspopup="true"
                        aria-expanded={collectionsMenuOpen}
                    >
                        <Icon name="folder" size={16} />
                        <span>{$_('nav.collections')}</span>
                    </button>
                    {#if collectionsMenuOpen}
                        <div class="nav-lists-dropdown" role="menu">
                            <a href="/collections" role="menuitem" onclick={() => { collectionsMenuOpen = false; closeMenu(); }}>
                                {$_('nav.all_collections')}
                            </a>
                            {#each navCollections as col}
                                <a href="/collections/{col.id}" role="menuitem" onclick={() => { collectionsMenuOpen = false; closeMenu(); }}>
                                    {col.name}
                                </a>
                            {/each}
                            <a href="/collections?new=1" role="menuitem" class="add-collection-link" onclick={() => { collectionsMenuOpen = false; closeMenu(); }}>
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
                    <Icon name="list" size={16} />
                    <span>{$_('nav.lists')}</span>
                </button>
                {#if listsMenuOpen}
                    <div class="nav-lists-dropdown" role="menu">
                        <a href="/lists" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('nav.all_lists')}
                        </a>
                        <a href="/lists/groceries" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.groceries')}
                        </a>
                        <a href="/lists/hardware" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.hardware')}
                        </a>
                        <a href="/lists/home_goods" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.home_goods')}
                        </a>
                        <a href="/lists/wish_list" role="menuitem" onclick={() => { listsMenuOpen = false; closeMenu(); }}>
                            {$_('lists.type.wish_list')}
                        </a>
                    </div>
                {/if}
            </div>
            <a href="/stores" class="nav-link" onclick={closeMenu}>
                <Icon name="store" size={16} />
                <span>{$_('nav.stores')}</span>
            </a>
            <a href="/tasks" class="nav-link" onclick={closeMenu}>
                <Icon name="calendar-clock" size={16} />
                <span>{$_('nav.tasks')}</span>
            </a>
            <a href="/settings/appearance" class="nav-link" onclick={closeMenu}>
                <Icon name="settings" size={16} />
                <span>{$_('nav.settings')}</span>
            </a>
            <a href="/profile" class="user nav-link" onclick={closeMenu} title={$_('nav.edit_profile')}>
                <Icon name="user" size={16} />
                <span>{userLabel($me)}</span>
            </a>
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

<Toast />

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
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 700;
        font-size: 1.25rem;
        color: var(--text);
    }
    .brand-logo {
        display: block;
        width: 28px;
        height: 28px;
        /* Add drop-shadow so the shield stands out against any header surface color */
        filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.55)) drop-shadow(0 0 1px rgba(0, 0, 0, 0.35));
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
        justify-content: center;
        cursor: pointer;
        min-width: var(--tap-min);
        min-height: var(--tap-min);
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
    .nav-link {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
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
        /* Prevent child content from creating horizontal page scroll */
        overflow-x: hidden;
        min-width: 0;
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
