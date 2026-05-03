import { writable } from 'svelte/store';
import { api, type User, type PublicConfig } from './api';
import { setLocale } from './i18n';

export const me = writable<User | null>(null);
export const publicConfig = writable<PublicConfig | null>(null);

export async function refreshMe(): Promise<User | null> {
    try {
        const user = await api.get<User>('/auth/me');
        me.set(user);
        if (user.locale) setLocale(user.locale);
        return user;
    } catch {
        me.set(null);
        return null;
    }
}

export async function loadPublicConfig(): Promise<PublicConfig | null> {
    try {
        const cfg = await api.get<PublicConfig>('/config/public');
        publicConfig.set(cfg);
        return cfg;
    } catch {
        publicConfig.set(null);
        return null;
    }
}

export async function logout(): Promise<void> {
    await api.post('/auth/logout');
    me.set(null);
}
