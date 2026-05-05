<script lang="ts">
    import { toasts, type Toast } from './toast';
    import Icon from './Icon.svelte';

    const KIND_ICON: Record<Toast['kind'], string> = {
        error:   'circle-x',
        success: 'check-circle',
        warning: 'triangle-alert',
        info:    'info',
    };
</script>

<div class="toast-host" aria-live="polite" aria-atomic="false">
    {#each $toasts as toast (toast.id)}
        <div class="toast toast-{toast.kind}" role="status">
            <span class="toast-icon">
                <Icon name={KIND_ICON[toast.kind]} size={15} />
            </span>
            <span class="toast-message">{toast.message}</span>
        </div>
    {/each}
</div>

<style>
    .toast-host {
        position: fixed;
        bottom: 1.5rem;
        left: 50%;
        transform: translateX(-50%);
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
        z-index: 9999;
        pointer-events: none;
        align-items: center;
        width: max-content;
        max-width: min(480px, 90vw);
    }

    .toast {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.65rem 1.1rem;
        border-radius: 8px;
        background: var(--surface-2);
        color: var(--text);
        font-size: 0.875rem;
        line-height: 1.4;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
        border: 1px solid var(--border);
        animation: toast-in-out 4s ease forwards;
        width: 100%;
    }

    .toast-error {
        background: color-mix(in srgb, var(--danger) 18%, var(--surface));
        border-color: var(--danger);
        color: var(--text);
    }

    .toast-success {
        background: color-mix(in srgb, var(--success) 18%, var(--surface));
        border-color: var(--success);
        color: var(--text);
    }

    .toast-warning {
        background: color-mix(in srgb, #f59e0b 18%, var(--surface));
        border-color: #f59e0b;
        color: var(--text);
    }

    .toast-icon {
        flex-shrink: 0;
        font-size: 0.8rem;
        opacity: 0.85;
    }

    .toast-error .toast-icon   { color: var(--danger); }
    .toast-success .toast-icon { color: var(--success); }
    .toast-warning .toast-icon { color: #f59e0b; }

    @keyframes toast-in-out {
        0%   { opacity: 0; transform: translateY(16px); }
        8%   { opacity: 1; transform: translateY(0); }
        75%  { opacity: 1; }
        100% { opacity: 0; transform: translateY(-8px); }
    }
</style>
