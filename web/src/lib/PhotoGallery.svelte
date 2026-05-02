<script lang="ts">
    import { api } from '$lib/api';

    interface Photo {
        id: string;
        mime_type: string;
        sort_order: number;
        is_primary: boolean;
        caption: string | null;
        width: number | null;
        height: number | null;
    }

    let {
        itemId,
        canEdit = false,
        compact = false,
    }: {
        itemId: string;
        canEdit?: boolean;
        compact?: boolean;
    } = $props();

    let photos = $state<Photo[]>([]);
    let loaded = $state(false);
    let lightboxIdx = $state<number | null>(null);
    let uploading = $state(false);
    let editingCaption = $state<string | null>(null);
    let captionDraft = $state('');
    let dragFromIdx = $state<number | null>(null);

    function photoUrl(id: string) {
        return `/api/photos/${id}/download`;
    }

    async function load() {
        try {
            photos = await api.get<Photo[]>(`/items/${itemId}/photos`);
            photos = photos.slice().sort((a, b) => {
                if (a.is_primary !== b.is_primary) return a.is_primary ? -1 : 1;
                return a.sort_order - b.sort_order;
            });
        } catch {
            photos = [];
        }
        loaded = true;
    }

    $effect(() => {
        if (itemId) load();
    });

    async function upload(e: Event) {
        const files = (e.target as HTMLInputElement).files;
        if (!files || !files.length) return;
        uploading = true;
        try {
            const fd = new FormData();
            for (const f of Array.from(files)) fd.append('files', f);
            await api.upload(`/items/${itemId}/photos`, fd);
            await load();
        } catch {
            // non-fatal
        }
        uploading = false;
        (e.target as HTMLInputElement).value = '';
    }

    async function setPrimary(photo: Photo) {
        await api.patch(`/photos/${photo.id}`, { is_primary: true });
        await load();
    }

    async function deletePhoto(photo: Photo) {
        await api.delete(`/photos/${photo.id}`);
        photos = photos.filter(p => p.id !== photo.id);
        if (lightboxIdx !== null && lightboxIdx >= photos.length) lightboxIdx = photos.length - 1;
    }

    async function saveCaption(photo: Photo) {
        await api.patch(`/photos/${photo.id}`, { caption: captionDraft.trim() || null });
        photos = photos.map(p => p.id === photo.id ? { ...p, caption: captionDraft.trim() || null } : p);
        editingCaption = null;
    }

    function onDragStart(idx: number) {
        dragFromIdx = idx;
    }

    function onDragOver(e: DragEvent, idx: number) {
        e.preventDefault();
        if (dragFromIdx === null || dragFromIdx === idx) return;
        const reordered = [...photos];
        const [moved] = reordered.splice(dragFromIdx, 1);
        reordered.splice(idx, 0, moved);
        photos = reordered;
        dragFromIdx = idx;
    }

    async function onDragEnd() {
        dragFromIdx = null;
        if (!canEdit) return;
        const payload = photos.map((p, i) => ({ id: p.id, sort_order: i * 10 }));
        try {
            await api.put(`/items/${itemId}/photos/reorder`, payload);
            photos = photos.map((p, i) => ({ ...p, sort_order: i * 10 }));
        } catch {
            await load();
        }
    }

    function prevLightbox() {
        if (lightboxIdx === null) return;
        lightboxIdx = (lightboxIdx - 1 + photos.length) % photos.length;
    }

    function nextLightbox() {
        if (lightboxIdx === null) return;
        lightboxIdx = (lightboxIdx + 1) % photos.length;
    }

    function onLightboxKey(e: KeyboardEvent) {
        if (e.key === 'ArrowLeft') prevLightbox();
        else if (e.key === 'ArrowRight') nextLightbox();
        else if (e.key === 'Escape') lightboxIdx = null;
    }
</script>

{#if !loaded}
    <!-- photos load silently -->
{:else if photos.length > 0 || canEdit}
    <div class="gallery" class:compact>
        <div class="gallery-strip">
            {#each photos as photo, idx (photo.id)}
                <button
                    class="thumb-btn"
                    class:primary-thumb={photo.is_primary}
                    class:dragging={dragFromIdx === idx}
                    draggable={canEdit}
                    ondragstart={() => onDragStart(idx)}
                    ondragover={(e) => onDragOver(e, idx)}
                    ondragend={onDragEnd}
                    onclick={() => (lightboxIdx = idx)}
                    title={photo.caption ?? ''}
                >
                    <img src={photoUrl(photo.id)} alt={photo.caption ?? ''} loading="lazy" />
                </button>
            {/each}
            {#if canEdit}
                <label class="upload-btn" title="Add photos">
                    {#if uploading}…{:else}+{/if}
                    <input type="file" accept="image/*" multiple onchange={upload} style="display:none" />
                </label>
            {/if}
        </div>
    </div>
{/if}

{#if lightboxIdx !== null}
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <div
        class="lightbox-backdrop"
        role="dialog"
        aria-modal="true"
        onclick={() => (lightboxIdx = null)}
        onkeydown={onLightboxKey}
        tabindex="-1"
    >
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div class="lightbox" onclick={(e) => e.stopPropagation()}>
            {#if photos.length > 1}
                <button class="lb-nav lb-prev" onclick={prevLightbox} aria-label="Previous">&#8249;</button>
                <button class="lb-nav lb-next" onclick={nextLightbox} aria-label="Next">&#8250;</button>
            {/if}
            <button class="lb-close" onclick={() => (lightboxIdx = null)} aria-label="Close">&#x2715;</button>
            <img
                src={photoUrl(photos[lightboxIdx].id)}
                alt={photos[lightboxIdx].caption ?? ''}
                class="lb-img"
            />
            <div class="lb-footer">
                {#if editingCaption === photos[lightboxIdx].id}
                    <input
                        class="lb-caption-input"
                        bind:value={captionDraft}
                        placeholder="Add a caption…"
                        onblur={() => saveCaption(photos[lightboxIdx!])}
                        onkeydown={(e) => { if (e.key === 'Enter') saveCaption(photos[lightboxIdx!]); if (e.key === 'Escape') editingCaption = null; }}
                    />
                {:else}
                    <span
                        class="lb-caption"
                        role="button"
                        tabindex={canEdit ? 0 : -1}
                        onclick={() => { if (canEdit) { editingCaption = photos[lightboxIdx!].id; captionDraft = photos[lightboxIdx!].caption ?? ''; } }}
                        onkeydown={(e) => { if (canEdit && e.key === 'Enter') { editingCaption = photos[lightboxIdx!].id; captionDraft = photos[lightboxIdx!].caption ?? ''; } }}
                    >{photos[lightboxIdx].caption || (canEdit ? 'Click to add caption…' : '')}</span>
                {/if}
                <span class="lb-counter muted">{lightboxIdx + 1} / {photos.length}</span>
                {#if canEdit}
                    <div class="lb-actions">
                        {#if !photos[lightboxIdx].is_primary}
                            <button class="secondary" onclick={() => setPrimary(photos[lightboxIdx!])}>Set as primary</button>
                        {:else}
                            <span class="muted">Primary</span>
                        {/if}
                        <button class="danger" onclick={() => deletePhoto(photos[lightboxIdx!])}>Delete</button>
                    </div>
                {/if}
            </div>
        </div>
    </div>
{/if}

<style>
    .gallery { margin: 0.5rem 0 0; }
    .gallery-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
    }
    .gallery.compact .gallery-strip { gap: 4px; }

    .thumb-btn {
        display: block;
        width: 64px;
        height: 64px;
        border: 2px solid transparent;
        border-radius: 6px;
        overflow: hidden;
        padding: 0;
        cursor: pointer;
        background: var(--surface-2, #eee);
        flex-shrink: 0;
    }
    .gallery.compact .thumb-btn { width: 48px; height: 48px; }
    .thumb-btn.primary-thumb { border-color: var(--accent, #3b82f6); }
    .thumb-btn.dragging { opacity: 0.4; cursor: grabbing; }
    .thumb-btn[draggable="true"] { cursor: grab; }
    .thumb-btn img { width: 100%; height: 100%; object-fit: cover; display: block; }

    .upload-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        border: 2px dashed var(--border, #ccc);
        border-radius: 6px;
        cursor: pointer;
        font-size: 1.5rem;
        color: var(--muted, #888);
        flex-shrink: 0;
    }
    .gallery.compact .upload-btn { width: 48px; height: 48px; }

    /* Lightbox */
    .lightbox-backdrop {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,0.85);
        z-index: 1000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .lightbox {
        position: relative;
        max-width: min(90vw, 1200px);
        max-height: 90vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 0.75rem;
    }
    .lb-img {
        max-width: 100%;
        max-height: 75vh;
        border-radius: 8px;
        object-fit: contain;
    }
    .lb-footer {
        display: flex;
        align-items: center;
        gap: 1rem;
        flex-wrap: wrap;
        width: 100%;
        justify-content: center;
    }
    .lb-caption {
        color: #fff;
        font-size: 0.9rem;
        cursor: pointer;
        min-width: 4rem;
        text-align: center;
    }
    .lb-caption-input {
        background: rgba(255,255,255,0.1);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 4px;
        padding: 0.25rem 0.5rem;
        font-size: 0.9rem;
        min-width: 200px;
    }
    .lb-counter { color: rgba(255,255,255,0.5); font-size: 0.8rem; }
    .lb-actions { display: flex; gap: 0.5rem; }
    .lb-nav {
        position: absolute;
        top: 50%;
        transform: translateY(-50%);
        background: rgba(0,0,0,0.5);
        border: none;
        color: #fff;
        font-size: 2rem;
        padding: 0.5rem 0.8rem;
        border-radius: 4px;
        cursor: pointer;
        z-index: 2;
    }
    .lb-prev { left: -3.5rem; }
    .lb-next { right: -3.5rem; }
    .lb-close {
        position: absolute;
        top: -2.5rem;
        right: 0;
        background: none;
        border: none;
        color: #fff;
        font-size: 1.5rem;
        cursor: pointer;
    }
    .muted { color: var(--muted, #888); }
</style>
