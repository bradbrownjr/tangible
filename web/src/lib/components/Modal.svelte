<!-- Accessible focus-trapped modal dialog.
     Usage:
       <Modal bind:open title="Edit item" onclose={() => open = false}>
           ... content ...
           <svelte:fragment slot="footer">
               <Button onclick={save}>Save</Button>
           </svelte:fragment>
       </Modal>
-->
<script lang="ts">
    import type { Snippet } from 'svelte';
    import { tick } from 'svelte';
    import IconButton from './IconButton.svelte';

    interface Props {
        open?: boolean;
        title?: string;
        width?: string;
        onclose?: () => void;
        children: Snippet;
        footer?: Snippet;
    }

    let { open = false, title, width = '34rem', onclose, children, footer }: Props = $props();

    let dialogEl: HTMLDialogElement | undefined;

    $effect(() => {
        if (!dialogEl) return;
        if (open) {
            dialogEl.showModal();
        } else {
            dialogEl.close();
        }
    });

    async function handleClose() {
        await tick();
        onclose?.();
    }

    function handleBackdrop(e: MouseEvent) {
        if (e.target === dialogEl) onclose?.();
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === 'Escape') onclose?.();
    }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog
    bind:this={dialogEl}
    class="modal"
    style="max-width: {width}"
    onclose={handleClose}
    onclick={handleBackdrop}
    onkeydown={handleKeydown}
>
    {#if title}
        <header class="modal__header">
            <h2 class="modal__title">{title}</h2>
            <IconButton name="x" label="Close" btnSize="sm" onclick={() => onclose?.()} />
        </header>
    {/if}

    <div class="modal__body">
        {@render children()}
    </div>

    {#if footer}
        <footer class="modal__footer">
            {@render footer()}
        </footer>
    {/if}
</dialog>

<style>
    dialog.modal {
        width: min(var(--modal-width, 34rem), calc(100vw - 2rem));
        background: var(--surface);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        padding: 0;
        box-shadow: var(--shadow-lg);
        position: fixed;
        top: 50%;
        left: 50%;
        translate: -50% -50%;
        margin: 0;
    }

    dialog.modal::backdrop {
        background: rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(2px);
    }

    .modal__header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--space-4) var(--space-5);
        border-bottom: 1px solid var(--border);
    }

    .modal__title {
        margin: 0;
        font-size: var(--text-lg);
        font-weight: 700;
    }

    .modal__body {
        padding: var(--space-5);
    }

    .modal__footer {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: var(--space-3);
        padding: var(--space-4) var(--space-5);
        border-top: 1px solid var(--border);
        flex-wrap: wrap;
    }

    @media (max-width: 480px) {
        .modal__footer {
            flex-direction: column-reverse;
        }
        .modal__footer :global(button) {
            width: 100%;
        }
    }
</style>
