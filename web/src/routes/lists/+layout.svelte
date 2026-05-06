<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { onMount } from 'svelte';
    import { _ } from 'svelte-i18n';

    interface Props { children: import('svelte').Snippet; }
    let { children }: Props = $props();

    const TABS = [
        { id: 'groceries',  labelKey: 'lists.type.groceries' },
        { id: 'hardware',   labelKey: 'lists.type.hardware' },
        { id: 'home_goods', labelKey: 'lists.type.home_goods' },
        { id: 'wish_list',  labelKey: 'lists.type.wish_list' },
    ] as const;

    let tabsEl: HTMLDivElement | undefined;

    const activeType = $derived.by(() => {
        const m = page.url.pathname.match(/^\/lists\/([^/]+)/);
        return m ? m[1] : null;
    });

    // Scroll active tab into view
    $effect(() => {
        if (!tabsEl || !activeType) return;
        const btn = tabsEl.querySelector<HTMLButtonElement>(`[data-id="${activeType}"]`);
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
        if (!activeType) return;
        const dx = e.clientX - swipeStartX;
        const dy = e.clientY - swipeStartY;
        if (Math.abs(dx) < 50 || Math.abs(dy) > Math.abs(dx) * 0.7) return;

        const allIds = TABS.map((t) => t.id);
        const idx = allIds.indexOf(activeType as typeof allIds[number]);
        if (idx === -1) return;

        if (dx < 0 && idx < allIds.length - 1) {
            goto(`/lists/${allIds[idx + 1]}`);
        } else if (dx > 0 && idx > 0) {
            goto(`/lists/${allIds[idx - 1]}`);
        }
    }

    // Arrow key navigation
    function onKeydown(e: KeyboardEvent) {
        if (!tabsEl?.contains(e.target as Node)) return;
        if (!activeType) return;
        const allIds = TABS.map((t) => t.id);
        const idx = allIds.indexOf(activeType as typeof allIds[number]);
        if (idx === -1) return;
        if (e.key === 'ArrowRight' && idx < allIds.length - 1) {
            e.preventDefault();
            goto(`/lists/${allIds[idx + 1]}`);
        } else if (e.key === 'ArrowLeft' && idx > 0) {
            e.preventDefault();
            goto(`/lists/${allIds[idx - 1]}`);
        }
    }

    const LS_KEY = 'tangible:lastListTab';

    // Persist last-viewed list type
    $effect(() => {
        if (activeType) localStorage.setItem(LS_KEY, activeType);
    });

    onMount(() => {
        window.addEventListener('keydown', onKeydown);

        // On hydrate: if on /lists (no type), redirect to last-viewed type
        if (!activeType) {
            const last = localStorage.getItem(LS_KEY);
            const valid = TABS.map((t) => t.id) as string[];
            const target = last && valid.includes(last) ? last : 'groceries';
            goto(`/lists/${target}`, { replaceState: true });
        }

        return () => window.removeEventListener('keydown', onKeydown);
    });
</script>

<div class="lists-tabs-layout">
    {#if activeType}
        <div class="tab-strip-wrap" bind:this={tabsEl} role="tablist" aria-label={$_('nav.lists')}>
            {#each TABS as t (t.id)}
                <button
                    type="button"
                    role="tab"
                    class="tab"
                    class:tab--active={activeType === t.id}
                    aria-selected={activeType === t.id}
                    data-id={t.id}
                    onclick={() => goto(`/lists/${t.id}`)}
                >
                    {$_(t.labelKey)}
                </button>
            {/each}
        </div>

        <div
            class="tab-content"
            onpointerdown={onPointerDown}
            onpointerup={onPointerUp}
            role="tabpanel"
            aria-label={$_(TABS.find((t) => t.id === activeType)?.labelKey ?? 'nav.lists')}
        >
            {@render children()}
        </div>
    {:else}
        {@render children()}
    {/if}
</div>

<style>
    .lists-tabs-layout {
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
