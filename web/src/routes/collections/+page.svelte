<script lang="ts">
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Category, type Collection, type CollectionListPair } from '$lib/api';
    import { loadCategories, rootCategories } from '$lib/categories';
    import Icon from '$lib/Icon.svelte';

    const PRESET_ICON: Record<string, string> = {
        art_decor:      'palette',
        batteries:      'battery-charging',
        books:          'book-open',
        clothing:       'shirt',
        collectibles:   'star',
        fuel_chemicals: 'flask-conical',
        home_equipment: 'home',
        movies:         'film',
        music:          'music',
        other:          'grid-2x2',
        spices:         'shopping-cart',
        sports:         'activity',
        tabletop:       'dice-5',
        tools:          'wrench',
        vehicles:       'car',
        games:          'gamepad-2',
    };

    let collections = $state<Collection[]>([]);
    let categories = $state<Category[]>([]);
    let error = $state('');
    let loading = $state(true);

    // Wizard state — pickerOpen is derived from the URL so the + tab and All tab
    // are always in sync without requiring a page remount.
    const pickerOpen = $derived(page.url.searchParams.get('new') === '1');
    let chosen = $state<{ slug: string | null; name: string; description: string } | null>(null);
    let formName = $state('');
    let formDescription = $state('');
    let creating = $state(false);

    // Reset wizard state whenever the picker closes (URL no longer has ?new=1)
    $effect(() => {
        if (!pickerOpen) {
            chosen = null;
            formName = '';
            formDescription = '';
            error = '';
        }
    });

    const roots = $derived(rootCategories(categories));

    async function refresh() {
        try {
            collections = await api.get<Collection[]>('/collections');
            if (categories.length === 0) categories = await loadCategories();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    function openPicker() {
        goto('/collections?new=1');
    }

    function pickPreset(root: Category) {
        chosen = { slug: root.slug, name: root.name, description: root.description ?? '' };
        formName = root.name;
        formDescription = root.description ?? '';
    }

    function pickCustom() {
        chosen = { slug: null, name: '', description: '' };
        formName = '';
        formDescription = '';
    }

    function cancel() {
        goto('/collections', { replaceState: true });
    }

    async function create(e: Event) {
        e.preventDefault();
        if (!formName.trim()) return;
        creating = true;
        try {
            if (chosen?.slug) {
                // Preset: create a paired collection + list type
                const result = await api.post<CollectionListPair>('/lists/pairs', {
                    label: formName.trim(),
                    category_slug: chosen.slug,
                    description: formDescription.trim() || null
                });
                await refresh();
                goto(`/collections/${result.collection.id}`);
            } else {
                // Custom: collection only, no paired list type
                await api.post('/collections', {
                    name: formName.trim(),
                    description: formDescription.trim() || null,
                    default_category_slug: null
                });
                await refresh();
                goto('/collections', { replaceState: true });
            }
        } catch (e) {
            error = (e as Error).message;
        } finally {
            creating = false;
        }
    }

    onMount(async () => {
        await refresh();
    });
</script>

<h1>{$_('collections.title')}</h1>

{#if pickerOpen && !chosen}
    <div class="card" style="margin-bottom: 1.5rem">
        <h3 style="margin-top:0">{$_('collections.wizard_heading')}</h3>
        <p class="muted" style="margin-top:0; margin-bottom:1rem">
            {$_('collections.wizard_subtitle')}
        </p>
        <div class="presets">
            {#each roots as r (r.id)}
                <button type="button" class="preset" onclick={() => pickPreset(r)}>
                    <span class="preset-icon"><Icon name={PRESET_ICON[r.slug] ?? 'box'} size={24} /></span>
                    <strong>{r.name}</strong>
                    {#if r.description}<span class="muted">{r.description}</span>{/if}
                </button>
            {/each}
            <button type="button" class="preset preset-custom" onclick={pickCustom}>
                <span class="preset-icon"><Icon name="sparkles" size={24} /></span>
                <strong>{$_('collections.custom_preset_title')}</strong>
                <span class="muted">{$_('collections.custom_preset_subtitle')}</span>
            </button>
        </div>
        <p style="margin-top:1rem">
            <button type="button" class="link" onclick={cancel}>{$_('common.cancel')}</button>
        </p>
    </div>
{:else if pickerOpen && chosen}
    <form onsubmit={create} class="card" style="margin-bottom: 1.5rem">
        <h3 style="margin-top:0">
            {chosen.slug ? $_('collections.new_form_heading_preset', { values: { name: chosen.name } }) : $_('collections.new_form_heading_custom')}
        </h3>
        <div class="field">
            <label for="cname">{$_('collections.form_name_label')}</label>
            <input id="cname" bind:value={formName} placeholder={$_('collections.form_name_placeholder')} required />
        </div>
        <div class="field">
            <label for="cdesc">{$_('collections.form_description_label')}</label>
            <input id="cdesc" bind:value={formDescription} />
        </div>
        {#if chosen.slug}
            <p class="muted" style="margin: .25rem 0 1rem">
                {$_('collections.form_category_hint', { values: { slug: chosen.slug } })}
            </p>
        {/if}
        {#if error}<p class="error">{error}</p>{/if}
        <div style="display:flex; gap:.5rem">
            <button type="submit" disabled={creating}>{creating ? $_('collections.form_creating') : $_('collections.form_create')}</button>
            <button type="button" class="link" onclick={cancel}>{$_('common.cancel')}</button>
        </div>
    </form>
{/if}

{#if loading}
    <p class="muted">{$_('common.loading')}</p>
{:else}
    <div class="grid">
        {#each collections as c (c.id)}
            <a href={`/collections/${c.id}`} class="card collection">
                <Icon name={PRESET_ICON[c.default_category_slug ?? ''] ?? 'grid-2x2'} size={24} class="collection-icon" />
                <h3>{c.name}</h3>
                {#if c.description}<p class="muted">{c.description}</p>{/if}
                {#if c.default_category_slug}
                    <p class="badge">{c.default_category_slug}</p>
                {/if}
            </a>
        {/each}
        {#if !pickerOpen}
            <button type="button" class="card new-card" onclick={openPicker}>
                <Icon name="plus" size={24} />
                <span>{$_('collections.add_button')}</span>
            </button>
        {/if}
    </div>
{/if}

<style>
    .collection {
        display: flex;
        flex-direction: column;
        color: inherit;
    }
    :global(.collection-icon) {
        color: var(--accent);
        margin-bottom: 0.25rem;
    }
    .collection:hover {
        border-color: var(--accent);
        text-decoration: none;
    }
    h3 {
        margin: 0 0 0.5rem 0;
    }
    p {
        margin: 0;
    }
    .presets {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 0.5rem;
    }
    .preset {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        justify-content: flex-start;
        gap: 0.25rem;
        padding: 0.75rem;
        height: 9rem;
        overflow: hidden;
        text-align: left;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        cursor: pointer;
        color: inherit;
    }
    .preset-icon {
        color: var(--accent);
        margin-bottom: 0.25rem;
        line-height: 1;
    }
    .preset:hover {
        border-color: var(--accent);
    }
    .preset-custom {
        border-style: dashed;
    }
    .badge {
        display: inline-block;
        margin-top: 0.5rem;
        padding: 0.1rem 0.4rem;
        font-size: 0.75rem;
        border: 1px solid var(--border);
        border-radius: 4px;
        color: var(--muted);
    }
    .link {
        background: none;
        border: none;
        padding: 0;
        color: var(--accent);
        cursor: pointer;
    }
    .new-card {
        border-style: dashed;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        cursor: pointer;
        color: var(--accent);
        background: transparent;
        min-height: 7rem;
        font-size: 0.875rem;
    }
    .new-card:hover {
        background: color-mix(in srgb, var(--accent) 8%, transparent);
        border-color: var(--accent);
    }
</style>
