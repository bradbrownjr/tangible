<!-- Thin wrapper around lucide-svelte icon components.
     Usage: <Icon name="trash-2" size={18} />
            <Icon name="check" aria-label="Saved" /> -->
<script lang="ts">
    import * as lucide from 'lucide-svelte';

    interface Props {
        name: string;
        size?: number;
        strokeWidth?: number;
        color?: string;
        class?: string;
        'aria-label'?: string;
        'aria-hidden'?: boolean | 'true' | 'false';
    }

    let {
        name,
        size = 18,
        strokeWidth = 2,
        color = 'currentColor',
        class: cls = '',
        'aria-label': ariaLabel,
        'aria-hidden': ariaHidden,
    }: Props = $props();

    function toPascal(s: string): string {
        return s
            .split('-')
            .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
            .join('');
    }

    // Resolve to the Svelte icon component, or undefined for unknown names.
    // lucide-svelte v1.x icon components use legacy `$$props`, so we render
    // them directly via a value-binding (Svelte 5) instead of the deprecated
    // `<svelte:component>`, which fails to forward props to legacy components.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const IconComponent = $derived(lucide[toPascal(name) as keyof typeof lucide] as any);
</script>

{#if IconComponent}
    <IconComponent
        {size}
        {strokeWidth}
        {color}
        class={cls || undefined}
        aria-label={ariaLabel}
        aria-hidden={ariaHidden ?? (ariaLabel ? undefined : true)}
    />
{/if}
