// Theme management: mode (light/dark/system) + palette selection.
//
// Two keys are persisted in localStorage:
//   tangible:theme-mode    — 'light' | 'dark' | 'system'
//   tangible:theme-palette — a palette id from PALETTES below
//
// The resolved data-theme attribute is computed as:
//   single-mode palettes  → the palette id itself (e.g. 'gazette')
//   brand palette         → '<palette>-<mode>' (e.g. 'tangible-dark')
//
// The pre-hydration script in app.html must mirror this logic to avoid FOUC.

import { writable, type Writable } from 'svelte/store';

export type ThemeMode = 'light' | 'dark' | 'system';

export interface Palette {
    id: string;
    name: string;
    /** Dark-mode background hex for swatch preview */
    bg: string;
    /** Dark-mode accent hex for swatch preview */
    accent: string;
    /** Light-mode background hex for swatch preview */
    bgLight: string;
    /** Light-mode accent hex for swatch preview */
    accentLight: string;
}

export const PALETTES: Palette[] = [
    { id: 'tangible',   name: 'Tangible',   bg: '#1A1D29', accent: '#A78BFA', bgLight: '#F7F6FF', accentLight: '#7C3AED'  },
    { id: 'granite',    name: 'Granite',    bg: '#1D2327', accent: '#22A88E', bgLight: '#ECF2EF', accentLight: '#0F7A65'  },
    { id: 'gazette',    name: 'Gazette',    bg: '#1A2030', accent: '#60A5FA', bgLight: '#F2F7FF', accentLight: '#3B82F6'  },
    { id: 'paper',      name: 'Paper',      bg: '#1E1C18', accent: '#C4A97A', bgLight: '#F8F6F1', accentLight: '#AA9A73'  },
    { id: 'cloud',      name: 'Cloud',      bg: '#1A2328', accent: '#37BBE4', bgLight: '#F1F2F0', accentLight: '#37BBE4'  },
    { id: 'passion',    name: 'Passion',    bg: '#1A0A2E', accent: '#CE93D8', bgLight: '#F5F5F5', accentLight: '#8E24AA'  },
    { id: 'tron',       name: 'Tron',       bg: '#242B33', accent: '#6EE2FF', bgLight: '#EAF8FD', accentLight: '#0891B2'  },
    { id: 'espresso',   name: 'Espresso',   bg: '#21211F', accent: '#C49A6C', bgLight: '#FDF8F0', accentLight: '#8B6339'  },
    { id: 'onedark',    name: 'One Dark',   bg: '#282C34', accent: '#98C379', bgLight: '#F2F7EE', accentLight: '#3A7A22'  },
    { id: 'blues',      name: 'Blues',      bg: '#2B2C56', accent: '#6677EB', bgLight: '#EEF0FF', accentLight: '#4338CA'  },
    { id: 'blackboard', name: 'Blackboard', bg: '#1A1A1A', accent: '#FFB347', bgLight: '#FDFCF8', accentLight: '#C26800'  },
];

const MODE_KEY    = 'tangible:theme-mode';
const PALETTE_KEY = 'tangible:theme-palette';

function readMode(): ThemeMode {
    if (typeof localStorage === 'undefined') return 'system';
    const v = localStorage.getItem(MODE_KEY);
    return v === 'light' || v === 'dark' || v === 'system' ? v : 'system';
}

function readPalette(): string {
    if (typeof localStorage === 'undefined') return 'granite';
    return localStorage.getItem(PALETTE_KEY) ?? 'granite';
}

function systemPrefersDark(): boolean {
    if (typeof matchMedia === 'undefined') return true;
    return matchMedia('(prefers-color-scheme: dark)').matches;
}

function resolveMode(mode: ThemeMode): 'light' | 'dark' {
    if (mode === 'system') return systemPrefersDark() ? 'dark' : 'light';
    return mode;
}

export function resolveDataTheme(paletteId: string, mode: ThemeMode): string {
    return `${paletteId}-${resolveMode(mode)}`;
}

function applyTheme(paletteId: string, mode: ThemeMode): void {
    if (typeof document === 'undefined') return;
    const dataTheme = resolveDataTheme(paletteId, mode);
    document.documentElement.dataset.theme = dataTheme;

    // Update <meta name="theme-color"> from the resolved --bg CSS variable.
    requestAnimationFrame(() => {
        const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
        const meta = document.querySelector('meta[name="theme-color"]');
        if (meta && bg) meta.setAttribute('content', bg);
    });
}

export const theme: Writable<ThemeMode> = writable<ThemeMode>(
    typeof window === 'undefined' ? 'system' : readMode(),
);

export const palette: Writable<string> = writable<string>(
    typeof window === 'undefined' ? 'granite' : readPalette(),
);

let mediaListener: ((e: MediaQueryListEvent) => void) | null = null;

// Internal state for the combined subscriber.
let _currentMode: ThemeMode = 'system';
let _currentPalette: string = 'granite';

export function initTheme(): void {
    if (typeof window === 'undefined') return;

    theme.subscribe((mode) => {
        _currentMode = mode;
        try { localStorage.setItem(MODE_KEY, mode); } catch { /* private mode */ }
        applyTheme(_currentPalette, mode);

        const mq = matchMedia('(prefers-color-scheme: dark)');
        if (mediaListener) { mq.removeEventListener('change', mediaListener); mediaListener = null; }
        if (mode === 'system') {
            mediaListener = () => applyTheme(_currentPalette, _currentMode);
            mq.addEventListener('change', mediaListener);
        }
    });

    palette.subscribe((pal) => {
        _currentPalette = pal;
        try { localStorage.setItem(PALETTE_KEY, pal); } catch { /* private mode */ }
        applyTheme(pal, _currentMode);
    });
}

// Legacy compat — kept so any existing import of `resolve` still works.
export function resolve(mode: ThemeMode): 'light' | 'dark' {
    return resolveMode(mode);
}
