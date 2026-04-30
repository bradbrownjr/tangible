<script lang="ts">
    import { onMount } from 'svelte';

    let { onClose }: { onClose: () => void } = $props();

    let md = $state('');
    let loading = $state(true);
    let error = $state('');

    onMount(async () => {
        try {
            const res = await fetch('/api/changelog', { credentials: 'include' });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            md = await res.text();
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    });

    /** Tiny markdown → HTML renderer for our CHANGELOG dialect.
     *  Supported: # / ## / ### headings, - / * bullets, **bold**, `code`,
     *  [text](url) links, blank-line paragraphs. Escapes everything else. */
    function escapeHtml(s: string): string {
        return s
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function inline(s: string): string {
        let out = escapeHtml(s);
        out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
        out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        out = out.replace(
            /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener">$1</a>'
        );
        return out;
    }

    function render(src: string): string {
        const lines = src.split(/\r?\n/);
        const out: string[] = [];
        let inList = false;
        let currentLi: string | null = null;
        let para: string[] = [];

        const flushPara = () => {
            if (para.length) {
                out.push(`<p>${inline(para.join(' '))}</p>`);
                para = [];
            }
        };
        const flushLi = () => {
            if (currentLi !== null) {
                // Add a line break after a leading bold title ("**Foo.**  rest...")
                const liHtml = inline(currentLi).replace(
                    /^(<strong>[^<]+<\/strong>)\s+/,
                    '$1<br>'
                );
                out.push(`<li>${liHtml}</li>`);
                currentLi = null;
            }
        };
        const closeList = () => {
            if (inList) {
                flushLi();
                out.push('</ul>');
                inList = false;
            }
        };

        for (const raw of lines) {
            const line = raw.trimEnd();
            if (!line.trim()) {
                flushPara();
                closeList();
                continue;
            }
            const h = /^(#{1,6})\s+(.*)$/.exec(line);
            if (h) {
                flushPara();
                closeList();
                const level = h[1].length;
                out.push(`<h${level}>${inline(h[2])}</h${level}>`);
                continue;
            }
            const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
            if (bullet) {
                flushPara();
                flushLi();
                if (!inList) {
                    out.push('<ul>');
                    inList = true;
                }
                currentLi = bullet[1];
                continue;
            }
            // Continuation line for a multi-line list item
            if (inList && currentLi !== null) {
                currentLi += ' ' + line.trim();
                continue;
            }
            closeList();
            para.push(line);
        }
        flushPara();
        closeList();
        return out.join('\n');
    }

    const html = $derived(render(md));

    function onBackdropClick(e: MouseEvent) {
        if (e.target === e.currentTarget) onClose();
    }

    function onKey(e: KeyboardEvent) {
        if (e.key === 'Escape') onClose();
    }
</script>

<svelte:window onkeydown={onKey} />

<div
    class="backdrop"
    onclick={onBackdropClick}
    role="presentation"
>
    <div class="modal" role="dialog" aria-modal="true" aria-labelledby="whatsnew-title">
        <header>
            <h2 id="whatsnew-title">What's new</h2>
            <button class="close" onclick={onClose} aria-label="Close">×</button>
        </header>
        <div class="body">
            {#if loading}
                <p class="muted">Loading…</p>
            {:else if error}
                <p class="error">Couldn't load changelog: {error}</p>
            {:else}
                {@html html}
            {/if}
        </div>
    </div>
</div>

<style>
    .backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.55);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 50;
        padding: 1rem;
    }
    .modal {
        background: var(--surface);
        color: var(--text);
        border: 1px solid var(--border);
        border-radius: 0.75rem;
        max-width: 720px;
        width: 100%;
        max-height: 85vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
    }
    header {
        display: flex;
        align-items: center;
        padding: 0.75rem 1.25rem;
        border-bottom: 1px solid var(--border);
    }
    header h2 {
        margin: 0;
        font-size: 1.125rem;
        flex: 1;
    }
    .close {
        background: transparent;
        border: none;
        color: var(--text);
        font-size: 1.5rem;
        line-height: 1;
        cursor: pointer;
        padding: 0 0.5rem;
    }
    .body {
        padding: 1rem 1.5rem 1.5rem;
        overflow: auto;
    }
    .body :global(h1) {
        font-size: 1.25rem;
        margin: 1rem 0 0.5rem;
    }
    .body :global(h2) {
        font-size: 1.05rem;
        margin: 1.25rem 0 0.4rem;
        padding-top: 0.5rem;
        border-top: 1px solid var(--border);
    }
    .body :global(h3) {
        font-size: 0.95rem;
        margin: 0.75rem 0 0.25rem;
        color: var(--accent);
    }
    .body :global(ul) {
        margin: 0.25rem 0 0.75rem;
        padding-left: 1.25rem;
    }
    .body :global(li) {
        margin: 0.5rem 0;
    }
    .body :global(p) {
        margin: 0.4rem 0;
    }
    .body :global(code) {
        background: var(--code-bg, rgba(127, 127, 127, 0.15));
        padding: 0.05rem 0.3rem;
        border-radius: 0.25rem;
        font-size: 0.875em;
    }
</style>
