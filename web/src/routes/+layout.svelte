<script lang="ts">
    import '$lib/styles.css';
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { me, refreshMe, loadPublicConfig, logout } from '$lib/session';
    import { initTheme } from '$lib/theme';

    let { children } = $props();
    let ready = $state(false);

    onMount(async () => {
        initTheme();
        await Promise.all([refreshMe(), loadPublicConfig()]);
        ready = true;
        const path = $page.url.pathname;
        const onAuth = path === '/login' || path === '/register';
        if (!$me && !onAuth) {
            await goto('/login');
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
    <nav>
        {#if $me}
            <a href="/">Collections</a>
            <a href="/import">Import</a>
            <a href="/settings">Settings</a>
            <span class="user muted">{$me.username}</span>
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
    nav {
        display: flex;
        gap: 1rem;
        align-items: center;
        margin-left: auto;
    }
    .user {
        font-size: 0.875rem;
    }
    main {
        padding: 1.5rem;
        max-width: 1100px;
        margin: 0 auto;
    }
</style>
