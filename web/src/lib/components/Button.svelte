<!-- Semantic button component with variant + size support.
     Renders a <button> or an <a> when href is supplied.

     Variants: primary (default) | secondary | danger | ghost
     Sizes:    md (default) | sm | lg
-->
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
        size?: 'sm' | 'md' | 'lg';
        href?: string;
        type?: 'button' | 'submit' | 'reset';
        disabled?: boolean;
        loading?: boolean;
        class?: string;
        style?: string;
        onclick?: (e: MouseEvent) => void;
        children: Snippet;
    }

    let {
        variant = 'primary',
        size = 'md',
        href,
        type = 'button',
        disabled = false,
        loading = false,
        class: cls = '',
        style,
        onclick,
        children,
    }: Props = $props();

    const isDisabled = $derived(disabled || loading);
    const classes = $derived(
        ['btn', `btn--${variant}`, `btn--${size}`, cls].filter(Boolean).join(' '),
    );
</script>

{#if href}
    <a {href} class={classes} {style} aria-disabled={isDisabled || undefined}>
        {@render children()}
    </a>
{:else}
    <button
        {type}
        class={classes}
        {style}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        {onclick}
    >
        {#if loading}
            <span class="btn__spinner" aria-hidden="true"></span>
        {/if}
        {@render children()}
    </button>
{/if}

<style>
    .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: var(--space-2);
        border: none;
        border-radius: var(--radius-md);
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        transition: background 0.15s, opacity 0.15s;
        white-space: nowrap;
    }

    /* Sizes */
    .btn--sm { font-size: var(--text-sm); padding: 0.25rem 0.625rem; min-height: 32px; }
    .btn--md { font-size: var(--text-base); padding: 0.5rem 1rem;    min-height: var(--tap-min); }
    .btn--lg { font-size: var(--text-lg);  padding: 0.625rem 1.25rem; min-height: 52px; }

    /* Variants */
    .btn--primary   { background: var(--accent); color: var(--accent-contrast); }
    .btn--primary:hover   { background: var(--accent-hover); }
    .btn--secondary { background: var(--surface-2); color: var(--text); }
    .btn--secondary:hover { background: color-mix(in srgb, var(--surface-2) 80%, var(--text) 20%); }
    .btn--danger    { background: var(--danger); color: #fff; }
    .btn--danger:hover    { background: color-mix(in srgb, var(--danger) 85%, #000 15%); }
    .btn--ghost     { background: transparent; color: var(--text); border: 1px solid var(--border); }
    .btn--ghost:hover     { background: color-mix(in srgb, var(--text) 8%, transparent); }

    .btn:disabled,
    .btn[aria-disabled='true'] { opacity: 0.5; cursor: not-allowed; pointer-events: none; }

    /* Loading spinner */
    .btn__spinner {
        width: 1em;
        height: 1em;
        border: 2px solid currentColor;
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 0.6s linear infinite;
        flex-shrink: 0;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
</style>
