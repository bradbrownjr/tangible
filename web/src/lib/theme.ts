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
    /** 'light' | 'dark' | 'both' — 'both' means this palette defines light+dark variants */
    mode: 'light' | 'dark' | 'both';
    /** Representative background hex for swatch preview */
    bg: string;
    /** Representative accent hex for swatch preview */
    accent: string;
}

export const PALETTES: Palette[] = [
    // Brand palette (light + dark variants, mode-switchable)
    { id: 'tangible', name: 'Tangible',    mode: 'both',  bg: '#1A1D29', accent: '#A78BFA' },
    // Light-only
    { id: 'gazette',  name: 'Gazette',     mode: 'light', bg: '#F2F7FF', accent: '#3B82F6' },
    { id: 'paper',    name: 'Paper',       mode: 'light', bg: '#F8F6F1', accent: '#AA9A73' },
    { id: 'cloud',    name: 'Cloud',       mode: 'light', bg: '#F1F2F0', accent: '#37BBE4' },
    { id: 'passion',  name: 'Passion',     mode: 'light', bg: '#F5F5F5', accent: '#8E24AA' },
    // Dark-only
    { id: 'tron',       name: 'Tron',       mode: 'dark', bg: '#242B33', accent: '#6EE2FF' },
    { id: 'espresso',   name: 'Espresso',   mode: 'dark', bg: '#21211F', accent: '#C49A6C' },
    { id: 'onedark',    name: 'One Dark',   mode: 'dark', bg: '#282C34', accent: '#98C379' },
    { id: 'blues',      name: 'Blues',      mode: 'dark', bg: '#2B2C56', accent: '#6677EB' },
    { id: 'blackboard', name: 'Blackboard', mode: 'dark', bg: '#1A1A1A', accent: '#FFB347' },
];

const MODE_KEY    = 'tangible:theme-mode';
const PALETTE_KEY = 'tangible:theme-palette';

function readMode(): ThemeMode {
    if (typeof localStorage === 'undefined') return 'system';
    const v = localStorage.getItem(MODE_KEY);
    return v === 'light' || v === 'dark' || v === 'system' ? v : 'system';
}

function readPalette(): string {
    if (typeof localStorage === 'undefined') return 'tangible';
    return localStorage.getItem(PALETTE_KEY) ?? 'tangible';
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
    const palette = PALETTES.find((p) => p.id === paletteId) ?? PALETTES[0];
    if (palette.mode === 'both') {
        return `${paletteId}-${resolveMode(mode)}`;
    }
    // Single-mode palette: ignore mode, return id directly.
    return paletteId;
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
    typeof window === 'undefined' ? 'tangible' : readPalette(),
);

let mediaListener: ((e: MediaQueryListEvent) => void) | null = null;

// Internal state for the combined subscriber.
let _currentMode: ThemeMode = 'system';
let _currentPalette: string = 'tangible';

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
