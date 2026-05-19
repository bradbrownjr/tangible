<script lang="ts">
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Category, type UserListType, type CollectionListPair } from '$lib/api';
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

    let listTypes = $state<UserListType[]>([]);
    let categories = $state<Category[]>([]);
    let counts = $state<Record<string, number>>({});
    let loading = $state(true);
    let error = $state('');

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
            const [types, cats, countData] = await Promise.all([
                api.get<UserListType[]>('/lists/types'),
                loadCategories(),
                api.get<{ by_type: Record<string, number> }>('/lists/count'),
            ]);
            listTypes = types;
            categories = cats;
            counts = countData.by_type ?? {};
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    function openPicker() {
        goto('/lists?new=1');
    }

    function pickPreset(root: Category) {
        chosen = { slug: root.slug, name: root.name, description: root.description ?? '' };
        formName = root.name;
        formDescription = root.description ?? '';
    }

    function cancel() {
        goto('/lists', { replaceState: true });
    }

    async function create(e: Event) {
        e.preventDefault();
        if (!formName.trim()) return;
        creating = true;
        try {
            const result = await api.post<CollectionListPair>('/lists/pairs', {
                label: formName.trim(),
                category_slug: chosen?.slug ?? null,
                description: formDescription.trim() || null,
            });
            listTypes = [...listTypes, result.list_type];
            goto(`/lists/${result.list_type.slug}`);
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

<h1>{$_('nav.lists')}</h1>

{#if pickerOpen && !chosen}
    <div class="card" style="margin-bottom: 1.5rem">
        <h3 style="margin-top:0">{$_('lists.new_pair_title')}</h3>
        <p class="muted" style="margin-top:0; margin-bottom:1rem">
            {$_('lists.new_pair_subtitle')}
        </p>
        <div class="presets">
            {#each roots as r (r.id)}
                <button type="button" class="preset" onclick={() => pickPreset(r)}>
                    <span class="preset-icon"><Icon name={PRESET_ICON[r.slug] ?? 'box'} size={24} /></span>
                    <strong>{r.name}</strong>
                    {#if r.description}<span class="muted">{r.description}</span>{/if}
                </button>
            {/each}
        </div>
        <p style="margin-top:1rem">
            <button type="button" class="link" onclick={cancel}>{$_('common.cancel')}</button>
        </p>
    </div>
{:else if pickerOpen && chosen}
    <form onsubmit={create} class="card" style="margin-bottom: 1.5rem">
        <h3 style="margin-top:0">
            {$_('collections.new_form_heading_preset', { values: { name: chosen.name } })}
        </h3>
        <div class="field">
            <label for="lname">{$_('collections.form_name_label')}</label>
            <input id="lname" bind:value={formName} placeholder={$_('collections.form_name_placeholder')} required />
        </div>
        <div class="field">
            <label for="ldesc">{$_('collections.form_description_label')}</label>
            <input id="ldesc" bind:value={formDescription} />
        </div>
        {#if error}<p class="error">{error}</p>{/if}
        <div style="display:flex; gap:.5rem">
            <button type="submit" disabled={creating}>
                {creating ? $_('collections.form_creating') : $_('collections.form_create')}
            </button>
            <button type="button" class="link" onclick={cancel}>{$_('common.cancel')}</button>
        </div>
    </form>
{/if}

{#if loading}
    <p class="muted">{$_('common.loading')}</p>
{:else}
    <div class="presets">
        {#each listTypes as lt (lt.id)}
            <a href={`/lists/${lt.slug}`} class="preset preset-link">
                <span class="preset-icon">
                    <Icon name={PRESET_ICON[lt.category_slug ?? ''] ?? 'list'} size={24} />
                </span>
                <strong>{lt.label}</strong>
                {#if counts[lt.slug]}
                    <span class="badge">{counts[lt.slug]}</span>
                {/if}
            </a>
        {/each}
        <button type="button" class="preset preset-new" onclick={openPicker}>
            <Icon name="plus" size={24} />
            <span>{$_('lists.add_button')}</span>
        </button>
    </div>
{/if}

<style>
    h1 { margin: 0 0 1rem; }

    .presets {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 0.5rem;
        align-items: stretch;
    }

    .preset {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 0.25rem;
        padding: 0.75rem;
        min-height: 6rem;
        text-align: left;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 6px;
        cursor: pointer;
        color: inherit;
        position: relative;
    }
    .preset-icon {
        color: var(--accent);
        margin-bottom: 0.25rem;
        line-height: 1;
    }
    .preset:hover {
        border-color: var(--accent);
        text-decoration: none;
    }
    .preset-link {
        text-decoration: none;
    }
    .badge {
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background: var(--accent);
        color: var(--accent-contrast, white);
        border-radius: 999px;
        font-size: 0.75rem;
        padding: 0.05rem 0.45rem;
        min-width: 1.25rem;
        text-align: center;
    }

    .field {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        margin-bottom: 0.75rem;
    }
    .field label {
        font-size: var(--text-sm);
        color: var(--text-muted);
    }
    .field input {
        padding: 0.5rem 0.75rem;
        border: 1px solid var(--border);
        border-radius: var(--radius, 0.375rem);
        font-size: var(--text-base, 1rem);
        background: var(--surface);
        color: var(--text);
    }

    .link {
        background: none;
        border: none;
        padding: 0;
        color: var(--accent);
        cursor: pointer;
    }
    .preset-new {
        align-items: center;
        justify-content: center;
        border-style: dashed;
        color: var(--accent);
        background: transparent;
    }
    .preset-new:hover {
        background: color-mix(in srgb, var(--accent) 8%, transparent);
    }
    .error {
        color: var(--danger, #e53e3e);
        font-size: 0.875rem;
        margin: 0;
    }
</style>
