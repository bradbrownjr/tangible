<!-- Square icon-only button with tooltip support.
     Usage: <IconButton name="trash-2" label="Delete item" onclick={handler} />
-->
<script lang="ts">
    import Icon from '$lib/Icon.svelte';

    interface Props {
        name: string;
        label: string;
        size?: number;
        variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
        btnSize?: 'sm' | 'md';
        disabled?: boolean;
        type?: 'button' | 'submit';
        class?: string;
        onclick?: (e: MouseEvent) => void;
    }

    let {
        name,
        label,
        size = 16,
        variant = 'ghost',
        btnSize = 'md',
        disabled = false,
        type = 'button',
        class: cls = '',
        onclick,
    }: Props = $props();

    const classes = $derived(
        ['icon-btn', `icon-btn--${variant}`, `icon-btn--${btnSize}`, cls].filter(Boolean).join(' '),
    );
</script>

<button {type} class={classes} {disabled} aria-label={label} title={label} {onclick}>
    <Icon {name} {size} />
</button>

<style>
    .icon-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: none;
        border-radius: var(--radius-md);
        cursor: pointer;
        transition: background 0.15s;
        flex-shrink: 0;
    }

    .icon-btn--sm { width: 32px; height: 32px; min-height: 32px; }
    .icon-btn--md { width: var(--tap-min); height: var(--tap-min); min-height: var(--tap-min); }

    .icon-btn--primary   { background: var(--accent); color: var(--accent-contrast); }
    .icon-btn--primary:hover   { background: var(--accent-hover); }
    .icon-btn--secondary { background: var(--surface-2); color: var(--text); }
    .icon-btn--secondary:hover { background: color-mix(in srgb, var(--surface-2) 80%, var(--text) 20%); }
    .icon-btn--danger    { background: transparent; color: var(--danger); }
    .icon-btn--danger:hover    { background: color-mix(in srgb, var(--danger) 12%, transparent); }
    .icon-btn--ghost     { background: transparent; color: var(--text-muted); }
    .icon-btn--ghost:hover     { background: color-mix(in srgb, var(--text) 8%, transparent); color: var(--text); }

    .icon-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
