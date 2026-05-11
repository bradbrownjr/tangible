<script lang="ts">
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { onMount } from 'svelte';
    import { _ } from 'svelte-i18n';
    import { api, type UserListType } from '$lib/api';

    interface Props { children: import('svelte').Snippet; }
    let { children }: Props = $props();

    // User-defined list types fetched from the server.
    let customTypes = $state<UserListType[]>([]);

    async function loadCustomTypes() {
        try {
            customTypes = await api.get<UserListType[]>('/lists/types', true);
        } catch { /* silently ignore */ }
    }

    async function deleteCustomType(t: UserListType) {
        if (!confirm($_('lists.add_type_delete_confirm'))) return;
        try {
            await api.delete(`/lists/types/${t.id}`);
            customTypes = customTypes.filter((c) => c.id !== t.id);
            if (activeType === t.slug) goto('/lists');
        } catch { /* toast shown by client */ }
    }

    // All tab ids for swipe/keyboard nav: 'all' + each user list type slug
    const allTabIds = $derived(['all', ...customTypes.map((t) => t.slug)]);

    let tabsEl: HTMLDivElement | undefined = $state();

    const activeType = $derived.by(() => {
        const m = page.url.pathname.match(/^\/lists\/([^/]+)/);
        return m ? m[1] : 'all';
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
        const dx = e.clientX - swipeStartX;
        const dy = e.clientY - swipeStartY;
        if (Math.abs(dx) < 50 || Math.abs(dy) > Math.abs(dx) * 0.7) return;

        const idx = allTabIds.indexOf(activeType as string);
        if (idx === -1) return;

        if (dx < 0 && idx < allTabIds.length - 1) {
            const next = allTabIds[idx + 1];
            goto(next === 'all' ? '/lists' : `/lists/${next}`);
        } else if (dx > 0 && idx > 0) {
            const prev = allTabIds[idx - 1];
            goto(prev === 'all' ? '/lists' : `/lists/${prev}`);
        }
    }

    function onKeydown(e: KeyboardEvent) {
        if (!tabsEl?.contains(e.target as Node)) return;
        const idx = allTabIds.indexOf(activeType as string);
        if (idx === -1) return;
        if (e.key === 'ArrowRight' && idx < allTabIds.length - 1) {
            e.preventDefault();
            const next = allTabIds[idx + 1];
            goto(next === 'all' ? '/lists' : `/lists/${next}`);
        } else if (e.key === 'ArrowLeft' && idx > 0) {
            e.preventDefault();
            const prev = allTabIds[idx - 1];
            goto(prev === 'all' ? '/lists' : `/lists/${prev}`);
        }
    }

    const LS_KEY = 'tangible:lastListTab';

    // Persist last-viewed list type
    $effect(() => {
        if (activeType) localStorage.setItem(LS_KEY, activeType);
    });

    onMount(() => {
        loadCustomTypes();
        window.addEventListener('keydown', onKeydown);
        return () => window.removeEventListener('keydown', onKeydown);
    });
</script>

<div class="lists-tabs-layout">
    <div class="tab-strip-wrap" bind:this={tabsEl} role="tablist" aria-label={$_('nav.lists')}>
        <button
            type="button"
            role="tab"
            class="tab"
            class:tab--active={activeType === 'all'}
            aria-selected={activeType === 'all'}
            data-id="all"
            onclick={() => goto('/lists')}
        >
            {$_('lists.tab_all')}
        </button>
        {#each customTypes as ct (ct.id)}
            <button
                type="button"
                role="tab"
                class="tab tab--custom"
                class:tab--active={activeType === ct.slug}
                aria-selected={activeType === ct.slug}
                data-id={ct.slug}
                onclick={() => goto(`/lists/${ct.slug}`)}
            >
                {ct.label}
                <span
                    class="tab-del"
                    role="button"
                    tabindex="0"
                    aria-label="Remove {ct.label}"
                    onclick={(e) => { e.stopPropagation(); deleteCustomType(ct); }}
                    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); deleteCustomType(ct); } }}
                >×</span>
            </button>
        {/each}
    </div>

    <div
        class="tab-content"
        onpointerdown={onPointerDown}
        onpointerup={onPointerUp}
        role="tabpanel"
        tabindex="0"
        aria-label={activeType}
    >
        {@render children()}
    </div>
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
        gap: 0.25rem;
        transition: color 0.15s, border-color 0.15s;
        margin-bottom: -1px;
    }
    .tab:hover { color: var(--text); }
    .tab--active {
        color: var(--accent);
        border-bottom-color: var(--accent);
    }

    .tab-del {
        font-size: 0.85rem;
        line-height: 1;
        opacity: 0.5;
        padding: 0 0.15rem;
        border-radius: 2px;
        cursor: pointer;
    }
    .tab-del:hover { opacity: 1; color: var(--danger, #e53e3e); }

    .tab-content {
        touch-action: pan-y;
    }

    @media (prefers-reduced-motion: reduce) {
        .tab { transition: none; }
    }
</style>