<script lang="ts">
    import { api } from '$lib/api';
    import { me, refreshMe } from '$lib/session';
    import { theme, palette, PALETTES, resolve, type ThemeMode } from '$lib/theme';
    import { _, locale } from 'svelte-i18n';
    import { LOCALES, setLocale } from '$lib/i18n';

    let selectedLocale = $state($me?.locale ?? $locale ?? 'en');
    $effect(() => { if ($me?.locale) selectedLocale = $me.locale; });

    async function changeLocale(code: string) {
        selectedLocale = code;
        setLocale(code);
        try {
            await api.patch('/auth/me', { locale: code });
            await refreshMe();
        } catch { /* non-fatal */ }
    }

    /** Resolved dark/light for swatch previews — reacts to theme store. */
    const resolvedMode = $derived(resolve($theme));
</script>

<h2>{$_('settings.nav_appearance')}</h2>

<div class="card">
    <h3 style="margin-top:0">{$_('settings.appearance_heading')}</h3>
    <p class="muted">{$_('settings.appearance_description')}</p>

    <div role="radiogroup" aria-label="Theme mode" class="theme-toggle" style="margin-bottom:1rem">
        {#each ['light', 'dark', 'system'] as const as opt (opt)}
            <button
                type="button"
                class={$theme === opt ? '' : 'secondary'}
                aria-pressed={$theme === opt}
                onclick={() => theme.set(opt as ThemeMode)}
            >
                {opt === 'light' ? $_('settings.theme_light') : opt === 'dark' ? $_('settings.theme_dark') : $_('settings.theme_system')}
            </button>
        {/each}
    </div>

    <p style="font-size:var(--text-sm);color:var(--text-muted);margin:0 0 0.5rem">{$_('settings.palette_label')}</p>
    <div class="palette-grid">
        {#each PALETTES as p (p.id)}
            {@const swatchBg     = resolvedMode === 'light' ? p.bgLight     : p.bg}
            {@const swatchAccent = resolvedMode === 'light' ? p.accentLight : p.accent}
            <button
                type="button"
                class="palette-card {$palette === p.id ? 'palette-card--active' : 'secondary'}"
                onclick={() => palette.set(p.id)}
                aria-pressed={$palette === p.id}
                title={p.name}
            >
                <span class="palette-swatch" style="background:{swatchBg}">
                    <span class="palette-accent" style="background:{swatchAccent}"></span>
                </span>
                <span class="palette-name">{p.name}</span>
            </button>
        {/each}
    </div>

    <div style="margin-top:0.75rem">
        <label for="lang-select" style="display:block;margin-bottom:0.35rem;font-size:0.875rem">{$_('settings.language_label')}</label>
        <select
            id="lang-select"
            value={selectedLocale}
            onchange={(e) => changeLocale((e.target as HTMLSelectElement).value)}
            style="width:auto"
        >
            {#each LOCALES as loc (loc.code)}
                <option value={loc.code}>{loc.label}</option>
            {/each}
        </select>
    </div>
</div>

<style>
    h2 { margin-top: 0; }

    .theme-toggle {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .palette-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
        gap: 0.5rem;
    }

    .palette-card {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.35rem;
        padding: 0.5rem;
        background: var(--surface-2);
        border: 2px solid transparent;
        border-radius: var(--radius-md);
        cursor: pointer;
        min-height: auto;
        transition: border-color 0.15s;
    }
    .palette-card--active {
        border-color: var(--accent);
    }

    .palette-swatch {
        width: 48px;
        height: 32px;
        border-radius: var(--radius-sm);
        border: 1px solid rgba(0,0,0,0.12);
        display: flex;
        align-items: flex-end;
        justify-content: flex-end;
        padding: 4px;
    }

    .palette-accent {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        border: 1.5px solid rgba(255,255,255,0.5);
    }

    .palette-name {
        font-size: var(--text-xs);
        color: var(--text-muted);
        text-align: center;
        line-height: 1.2;
    }
</style>
