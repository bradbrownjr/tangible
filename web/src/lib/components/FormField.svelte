<!-- Labelled form field wrapper with optional error and hint text.
     Usage:
       <FormField label="Title" error={errors.title} hint="Max 200 chars">
           <input bind:value={title} />
       </FormField>
-->
<script lang="ts">
    import type { Snippet } from 'svelte';

    interface Props {
        label: string;
        /** The id of the input/select inside so <label for> works correctly. */
        for?: string;
        error?: string | null;
        hint?: string;
        required?: boolean;
        class?: string;
        children: Snippet;
    }

    let { label, for: forId, error, hint, required = false, class: cls = '', children }: Props = $props();

    // Use provided id, or auto-generate one. Consumers should pass for={inputId}.
    const uid = forId ?? `ff-${Math.random().toString(36).slice(2, 7)}`;
</script>

<div class="form-field {cls}" class:form-field--error={!!error}>
    <label for={uid}>
        {label}{#if required}<span class="form-field__req" aria-hidden="true"> *</span>{/if}
    </label>
    <div class="form-field__control">
        {@render children()}
    </div>
    {#if error}
        <p class="form-field__error" role="alert">{error}</p>
    {:else if hint}
        <p class="form-field__hint">{hint}</p>
    {/if}
</div>

<style>
    .form-field { display: flex; flex-direction: column; gap: var(--space-1); }

    label {
        font-size: var(--text-sm);
        color: var(--text-muted);
        font-weight: 500;
    }

    .form-field__req { color: var(--danger); }

    .form-field__control :global(input),
    .form-field__control :global(select),
    .form-field__control :global(textarea) {
        width: 100%;
    }

    .form-field--error :global(input),
    .form-field--error :global(select),
    .form-field--error :global(textarea) {
        border-color: var(--danger);
        outline-color: var(--danger);
    }

    .form-field__error { font-size: var(--text-xs); color: var(--danger); margin: 0; }
    .form-field__hint  { font-size: var(--text-xs); color: var(--text-muted); margin: 0; }
</style>
