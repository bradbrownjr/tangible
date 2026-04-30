<script lang="ts">
    import '$lib/styles.css';
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { me, refreshMe, loadPublicConfig, logout, publicConfig } from '$lib/session';
    import { userLabel } from '$lib/api';
    import { get } from 'svelte/store';
    import { initTheme } from '$lib/theme';
    import WhatsNew from '$lib/WhatsNew.svelte';

    const SEEN_KEY = 'covet:whatsnew-seen-version';

    let { children } = $props();
    let ready = $state(false);
    let whatsNewOpen = $state(false);
    let lastSeen = $state<string | null>(null);

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
        const path = page.url.pathname;
        const onAuth = path === '/login' || path === '/register';
        const isPublic = path.startsWith('/share/') || path.startsWith('/invite/');
        if (!$me && !onAuth && !isPublic) {
            const cfg = get(publicConfig);
            await goto(cfg?.setup_required ? '/register' : '/login');
        } else if ($me && onAuth) {
            await goto('/');
        }
    });

    async function doLogout() {
        await logout();
        await goto('/login');
    }
</script>

<header>
    <a href="/" class="brand">Covet</a>
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
            <a href="/">Collections</a>
            <a href="/import">Import</a>
            <a href="/settings">Settings</a>
            <a href="/profile" class="user" title="Edit your profile">{userLabel($me)}</a>
            <button class="secondary" onclick={doLogout}>Log out</button>
        {/if}
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
</style>
