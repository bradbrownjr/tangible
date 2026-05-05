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
    }

    let {
        name,
        size = 18,
        strokeWidth = 2,
        color = 'currentColor',
        class: cls = '',
        'aria-label': ariaLabel,
    }: Props = $props();

    function toPascal(s: string): string {
        return s
            .split('-')
            .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
            .join('');
    }

    // Resolve to the Svelte icon component, or undefined for unknown names.
    // Cast via `unknown` to satisfy svelte:component's type while keeping the
    // lookup type-safe at the key level.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const IconComponent = $derived(lucide[toPascal(name) as keyof typeof lucide] as any);
</script>

{#if IconComponent}
    <svelte:component
        this={IconComponent}
        {size}
        {strokeWidth}
        {color}
        class={cls || undefined}
        aria-label={ariaLabel}
        aria-hidden={ariaLabel ? undefined : true}
    />
{/if}
