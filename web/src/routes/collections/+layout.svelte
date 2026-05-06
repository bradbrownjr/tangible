<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { onMount } from 'svelte';
    import { _ } from 'svelte-i18n';
    import { api, type Collection } from '$lib/api';
    import { me } from '$lib/session';

    interface Props { children: import('svelte').Snippet; }
    let { children }: Props = $props();

    let collections = $state<Collection[]>([]);
    let tabsEl: HTMLDivElement | undefined;

    // Active tab: 'all' or a collection id
    const activeId = $derived.by(() => {
        const m = page.url.pathname.match(/^\/collections\/([^/]+)/);
        return m ? m[1] : 'all';
    });

    async function loadCollections() {
        if (!$me) return;
        try {
            collections = await api.get<Collection[]>('/collections', true);
        } catch {
            collections = [];
        }
    }

    $effect(() => {
        // Re-fetch when the user changes (login/logout)
        $me;
        loadCollections();
    });

    // Persist last-visited tab
    $effect(() => {
        if (activeId) {
            localStorage.setItem('tangible:lastCollectionTab', activeId);
        }
    });

    // Scroll the active tab into view when it changes
    $effect(() => {
        if (!tabsEl) return;
        const btn = tabsEl.querySelector<HTMLButtonElement>(`[data-id="${activeId}"]`);
        btn?.scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    });

    // --- Swipe navigation ---
    let swipeStartX = 0;
    let swipeStartY = 0;
    let swiping = false;

    function onPointerDown(e: PointerEvent) {
        swipeStartX = e.clientX;
        swipeStartY = e.clientY;
        swiping = true;
    }

    function onPointerUp(e: PointerEvent) {
        if (!swiping) return;
        swiping = false;
        const dx = e.clientX - swipeStartX;
        const dy = e.clientY - swipeStartY;
        if (Math.abs(dx) < 50 || Math.abs(dy) > Math.abs(dx) * 0.7) return;

        const allIds = ['all', ...collections.map((c) => c.id)];
        const idx = allIds.indexOf(activeId);
        if (idx === -1) return;

        if (dx < 0 && idx < allIds.length - 1) {
            // Swipe left → next tab
            const next = allIds[idx + 1];
            goto(next === 'all' ? '/collections' : `/collections/${next}`);
        } else if (dx > 0 && idx > 0) {
            // Swipe right → previous tab
            const prev = allIds[idx - 1];
            goto(prev === 'all' ? '/collections' : `/collections/${prev}`);
        }
    }

    // Arrow key navigation (WAI-ARIA tabs pattern)
    function onKeydown(e: KeyboardEvent) {
        if (e.target !== tabsEl && !(tabsEl?.contains(e.target as Node))) return;
        const allIds = ['all', ...collections.map((c) => c.id)];
        const idx = allIds.indexOf(activeId);
        if (idx === -1) return;
        if (e.key === 'ArrowRight' && idx < allIds.length - 1) {
            e.preventDefault();
            const next = allIds[idx + 1];
            goto(next === 'all' ? '/collections' : `/collections/${next}`);
        } else if (e.key === 'ArrowLeft' && idx > 0) {
            e.preventDefault();
            const prev = allIds[idx - 1];
            goto(prev === 'all' ? '/collections' : `/collections/${prev}`);
        }
    }

    onMount(() => {
        window.addEventListener('keydown', onKeydown);
        return () => window.removeEventListener('keydown', onKeydown);
    });
</script>

<div class="collections-tabs-layout">
    <div class="tab-strip-wrap" bind:this={tabsEl} role="tablist" aria-label={$_('collections.title')}>
        <button
            type="button"
            role="tab"
            class="tab"
            class:tab--active={activeId === 'all'}
            aria-selected={activeId === 'all'}
            data-id="all"
            onclick={() => goto('/collections')}
        >
            {$_('collections.tab_all')}
        </button>
        {#each collections as c (c.id)}
            <button
                type="button"
                role="tab"
                class="tab"
                class:tab--active={activeId === c.id}
                aria-selected={activeId === c.id}
                data-id={c.id}
                onclick={() => goto(`/collections/${c.id}`)}
            >
                {c.name}
            </button>
        {/each}
    </div>

    <div
        class="tab-content"
        onpointerdown={onPointerDown}
        onpointerup={onPointerUp}
        role="tabpanel"
        aria-label={activeId === 'all' ? $_('collections.tab_all') : (collections.find((c) => c.id === activeId)?.name ?? '')}
    >
        {@render children()}
    </div>
</div>

<style>
    .collections-tabs-layout {
        display: flex;
        flex-direction: column;
        min-height: 0;
    }

    .tab-strip-wrap {
        display: flex;
        gap: 0;
        border-bottom: 1px solid var(--border);
        overflow-x: auto;
        scrollbar-width: none;
        flex-shrink: 0;
        margin-bottom: 1.25rem;
    }
    .tab-strip-wrap::-webkit-scrollbar { display: none; }

    .tab {
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 0 var(--space-4);
        min-height: var(--tap-min);
        font-size: var(--text-sm);
        font-weight: 500;
        color: var(--text-muted);
        cursor: pointer;
        white-space: nowrap;
        border-radius: 0;
        display: inline-flex;
        align-items: center;
        transition: color 0.15s, border-color 0.15s;
        margin-bottom: -1px;
    }
    .tab:hover { color: var(--text); }
    .tab--active {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    .tab-content {
        touch-action: pan-y;
    }

    @media (prefers-reduced-motion: reduce) {
        .tab {
            transition: none;
        }
    }
</style>
