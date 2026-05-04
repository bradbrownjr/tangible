import { writable } from 'svelte/store';

export type ToastKind = 'info' | 'success' | 'error' | 'warning';

export interface Toast {
    id: number;
    message: string;
    kind: ToastKind;
}

let _nextId = 0;
export const toasts = writable<Toast[]>([]);

export function showToast(message: string, kind: ToastKind = 'info', duration = 4000): void {
    const id = _nextId++;
    toasts.update((t) => [...t, { id, message, kind }]);
    setTimeout(() => {
        toasts.update((t) => t.filter((toast) => toast.id !== id));
    }, duration);
}

export function showError(message: string): void {
    showToast(message, 'error', 5000);
}
