// Theme management: light / dark / system.
//
// The actual `data-theme` attribute is set on <html> by an inline script in
// app.html before hydration to avoid FOUC. This module is responsible for
// reactive updates after hydration and for persisting the user's preference.

import { writable, type Writable } from 'svelte/store';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'covet:theme';
const META_COLOR: Record<ResolvedTheme, string> = {
    dark: '#0f172a',
    light: '#f8fafc',
};

function readStored(): ThemeMode {
    if (typeof localStorage === 'undefined') return 'system';
    const v = localStorage.getItem(STORAGE_KEY);
    return v === 'light' || v === 'dark' || v === 'system' ? v : 'system';
}

function systemPrefersDark(): boolean {
    if (typeof matchMedia === 'undefined') return true;
    return matchMedia('(prefers-color-scheme: dark)').matches;
}

export function resolve(mode: ThemeMode): ResolvedTheme {
    if (mode === 'system') return systemPrefersDark() ? 'dark' : 'light';
    return mode;
}

function apply(resolved: ResolvedTheme): void {
    if (typeof document === 'undefined') return;
    document.documentElement.dataset.theme = resolved;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', META_COLOR[resolved]);
}

export const theme: Writable<ThemeMode> = writable<ThemeMode>(
    typeof window === 'undefined' ? 'system' : readStored(),
);

let mediaListener: ((e: MediaQueryListEvent) => void) | null = null;

export function initTheme(): void {
    if (typeof window === 'undefined') return;

    theme.subscribe((mode) => {
        try {
            localStorage.setItem(STORAGE_KEY, mode);
        } catch {
            /* storage may be unavailable (private mode) */
        }
        apply(resolve(mode));

        const mq = matchMedia('(prefers-color-scheme: dark)');
        if (mediaListener) {
            mq.removeEventListener('change', mediaListener);
            mediaListener = null;
        }
        if (mode === 'system') {
            mediaListener = (e) => apply(e.matches ? 'dark' : 'light');
            mq.addEventListener('change', mediaListener);
        }
    });
}
