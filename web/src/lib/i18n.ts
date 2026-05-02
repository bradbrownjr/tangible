import { addMessages, getLocaleFromNavigator, init, locale } from 'svelte-i18n';
import de from './locales/de.json';
import en from './locales/en.json';
import es from './locales/es.json';
import fr from './locales/fr.json';
import ja from './locales/ja.json';

type LocaleDict = Parameters<typeof addMessages>[1];

const STORAGE_KEY = 'covet:locale';

export const LOCALES: { code: string; label: string }[] = [
    { code: 'en', label: 'English' },
    { code: 'fr', label: 'Français' },
    { code: 'de', label: 'Deutsch' },
    { code: 'es', label: 'Español' },
    { code: 'ja', label: '日本語' },
];

export function initI18n(): void {
    addMessages('en', en as unknown as LocaleDict);
    addMessages('fr', fr as unknown as LocaleDict);
    addMessages('de', de as unknown as LocaleDict);
    addMessages('es', es as unknown as LocaleDict);
    addMessages('ja', ja as unknown as LocaleDict);

    let saved: string | null = null;
    try {
        saved = localStorage.getItem(STORAGE_KEY);
    } catch {
        // localStorage may be disabled
    }

    init({
        fallbackLocale: 'en',
        initialLocale: saved || getLocaleFromNavigator() || 'en',
    });
}

export function setLocale(code: string): void {
    locale.set(code);
    try {
        localStorage.setItem(STORAGE_KEY, code);
    } catch {
        // non-fatal
    }
}

export { locale };
