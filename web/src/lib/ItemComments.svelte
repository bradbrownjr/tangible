<script lang="ts">
    import { api, type ItemComment } from '$lib/api';

    let { itemId, currentUserId, canManage = false }: {
        itemId: string;
        currentUserId: string | undefined;
        /** true when the viewer is a collection editor/owner (can delete any comment) */
        canManage?: boolean;
    } = $props();

    let open = $state(false);
    let loaded = $state(false);
    let comments = $state<ItemComment[]>([]);
    let openReplies = $state<Record<string, ItemComment[]>>({});
    let loadingReplies = $state<Record<string, boolean>>({});
    let newBody = $state('');
    let submitting = $state(false);
    let error = $state('');
    let editingId = $state<string | null>(null);
    let editBody = $state('');
    let replyingTo = $state<string | null>(null);
    let replyBody = $state('');

    async function load() {
        comments = await api.get<ItemComment[]>(`/items/${itemId}/comments`);
        loaded = true;
    }

    async function toggle() {
        open = !open;
        if (open && !loaded) await load();
    }

    async function submit() {
        if (!newBody.trim()) return;
        submitting = true;
        error = '';
        try {
            const c = await api.post<ItemComment>(`/items/${itemId}/comments`, { body: newBody.trim() });
            comments = [c, ...comments];
            newBody = '';
        } catch (e) {
            error = (e as Error).message;
        } finally {
            submitting = false;
        }
    }

    async function submitReply(parentId: string) {
        if (!replyBody.trim()) return;
        submitting = true;
        error = '';
        try {
            const c = await api.post<ItemComment>(`/items/${itemId}/comments`, {
                body: replyBody.trim(),
                parent_id: parentId,
            });
            openReplies[parentId] = [...(openReplies[parentId] ?? []), c];
            // Increment reply_count on parent
            comments = comments.map((cm) =>
                cm.id === parentId ? { ...cm, reply_count: cm.reply_count + 1 } : cm
            );
            replyBody = '';
            replyingTo = null;
        } catch (e) {
            error = (e as Error).message;
        } finally {
            submitting = false;
        }
    }

    async function loadReplies(parentId: string) {
        if (openReplies[parentId]) {
            // Toggle closed
            const { [parentId]: _, ...rest } = openReplies;
            openReplies = rest;
            return;
        }
        loadingReplies = { ...loadingReplies, [parentId]: true };
        try {
            const rows = await api.get<ItemComment[]>(`/items/${itemId}/comments/${parentId}/replies`);
            openReplies = { ...openReplies, [parentId]: rows };
        } finally {
            loadingReplies = { ...loadingReplies, [parentId]: false };
        }
    }

    async function saveEdit(commentId: string) {
        if (!editBody.trim()) return;
        try {
            const updated = await api.patch<ItemComment>(`/comments/${commentId}`, { body: editBody.trim() });
            comments = comments.map((c) => (c.id === commentId ? updated : c));
            // Also update in reply lists if present
            for (const [pid, replies] of Object.entries(openReplies)) {
                openReplies[pid] = replies.map((r) => (r.id === commentId ? updated : r));
            }
        } catch (e) {
            error = (e as Error).message;
        }
        editingId = null;
        editBody = '';
    }

    async function deleteComment(commentId: string, parentId: string | null) {
        if (!confirm('Delete this comment?')) return;
        try {
            await api.delete(`/comments/${commentId}`);
            if (parentId) {
                openReplies[parentId] = (openReplies[parentId] ?? []).filter((r) => r.id !== commentId);
                comments = comments.map((c) =>
                    c.id === parentId ? { ...c, reply_count: Math.max(0, c.reply_count - 1) } : c
                );
            } else {
                comments = comments.filter((c) => c.id !== commentId);
            }
        } catch (e) {
            error = (e as Error).message;
        }
    }

    function timeAgo(iso: string): string {
        const diff = Date.now() - new Date(iso).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
    }

    const totalCount = $derived(comments.reduce((n, c) => n + 1 + c.reply_count, 0));
</script>

<div class="comments-section">
    <button class="comments-toggle secondary small" type="button" onclick={toggle}>
        {open ? '▲' : '▼'} Comments{totalCount > 0 ? ` (${totalCount})` : ''}
    </button>

    {#if open}
        <div class="comments-body">
            {#if error}<p class="error">{error}</p>{/if}

            {#if currentUserId}
                <div class="comment-compose">
                    <textarea
                        bind:value={newBody}
                        placeholder="Add a comment…"
                        rows={2}
                        onkeydown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submit(); }}
                    ></textarea>
                    <button type="button" onclick={submit} disabled={submitting || !newBody.trim()}>Post</button>
                </div>
            {/if}

            {#if !loaded}
                <p class="muted">Loading…</p>
            {:else if comments.length === 0}
                <p class="muted">No comments yet.</p>
            {:else}
                <ul class="comment-list">
                    {#each comments as c (c.id)}
                        <li class="comment-item">
                            {#if editingId === c.id}
                                <div class="comment-edit">
                                    <textarea bind:value={editBody} rows={2}></textarea>
                                    <div class="comment-edit-actions">
                                        <button type="button" onclick={() => saveEdit(c.id)} disabled={submitting}>Save</button>
                                        <button type="button" class="secondary" onclick={() => { editingId = null; editBody = ''; }}>Cancel</button>
                                    </div>
                                </div>
                            {:else}
                                <div class="comment-header">
                                    <span class="comment-author">{c.author.display_name ?? c.author.username}</span>
                                    <span class="comment-time muted">{timeAgo(c.created_at)}</span>
                                    {#if c.created_at !== c.updated_at}
                                        <span class="comment-edited muted">(edited)</span>
                                    {/if}
                                    <span class="comment-actions">
                                        {#if c.author.id === currentUserId}
                                            <button type="button" class="link-btn" onclick={() => { editingId = c.id; editBody = c.body; }}>Edit</button>
                                        {/if}
                                        {#if c.author.id === currentUserId || canManage}
                                            <button type="button" class="link-btn danger-link" onclick={() => deleteComment(c.id, null)}>Delete</button>
                                        {/if}
                                    </span>
                                </div>
                                <p class="comment-body">{c.body}</p>
                                <div class="comment-footer">
                                    {#if currentUserId}
                                        <button type="button" class="link-btn" onclick={() => { replyingTo = replyingTo === c.id ? null : c.id; replyBody = ''; }}>
                                            Reply
                                        </button>
                                    {/if}
                                    {#if c.reply_count > 0 || openReplies[c.id]}
                                        <button type="button" class="link-btn" onclick={() => loadReplies(c.id)}>
                                            {loadingReplies[c.id] ? 'Loading…' : openReplies[c.id] ? `Hide replies` : `${c.reply_count} repl${c.reply_count === 1 ? 'y' : 'ies'}`}
                                        </button>
                                    {/if}
                                </div>
                            {/if}

                            {#if replyingTo === c.id}
                                <div class="comment-compose reply-compose">
                                    <textarea bind:value={replyBody} placeholder="Write a reply…" rows={2} onkeydown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) submitReply(c.id); }}></textarea>
                                    <button type="button" onclick={() => submitReply(c.id)} disabled={submitting || !replyBody.trim()}>Reply</button>
                                    <button type="button" class="secondary" onclick={() => { replyingTo = null; replyBody = ''; }}>Cancel</button>
                                </div>
                            {/if}

                            {#if openReplies[c.id]}
                                <ul class="reply-list">
                                    {#each openReplies[c.id] as r (r.id)}
                                        <li class="comment-item reply-item">
                                            {#if editingId === r.id}
                                                <div class="comment-edit">
                                                    <textarea bind:value={editBody} rows={2}></textarea>
                                                    <div class="comment-edit-actions">
                                                        <button type="button" onclick={() => saveEdit(r.id)} disabled={submitting}>Save</button>
                                                        <button type="button" class="secondary" onclick={() => { editingId = null; editBody = ''; }}>Cancel</button>
                                                    </div>
                                                </div>
                                            {:else}
                                                <div class="comment-header">
                                                    <span class="comment-author">{r.author.display_name ?? r.author.username}</span>
                                                    <span class="comment-time muted">{timeAgo(r.created_at)}</span>
                                                    {#if r.created_at !== r.updated_at}
                                                        <span class="comment-edited muted">(edited)</span>
                                                    {/if}
                                                    <span class="comment-actions">
                                                        {#if r.author.id === currentUserId}
                                                            <button type="button" class="link-btn" onclick={() => { editingId = r.id; editBody = r.body; }}>Edit</button>
                                                        {/if}
                                                        {#if r.author.id === currentUserId || canManage}
                                                            <button type="button" class="link-btn danger-link" onclick={() => deleteComment(r.id, c.id)}>Delete</button>
                                                        {/if}
                                                    </span>
                                                </div>
                                                <p class="comment-body">{r.body}</p>
                                            {/if}
                                        </li>
                                    {/each}
                                </ul>
                            {/if}
                        </li>
                    {/each}
                </ul>
            {/if}
        </div>
    {/if}
</div>

<style>
    .comments-section {
        margin-top: 0.75rem;
        border-top: 1px solid var(--border, #e5e7eb);
        padding-top: 0.5rem;
    }
    .comments-toggle {
        font-size: 0.8rem;
        padding: 0.2rem 0.6rem;
        cursor: pointer;
    }
    .comments-body {
        margin-top: 0.5rem;
    }
    .comment-compose {
        display: flex;
        gap: 0.4rem;
        align-items: flex-start;
        margin-bottom: 0.75rem;
    }
    .comment-compose textarea {
        flex: 1;
        resize: vertical;
        font-size: 0.875rem;
        padding: 0.4rem 0.5rem;
    }
    .comment-list, .reply-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
    }
    .comment-item {
        padding: 0.4rem 0.5rem;
        border-radius: 4px;
        background: var(--surface-subtle, rgba(0,0,0,0.03));
    }
    .reply-list {
        margin-top: 0.4rem;
        margin-left: 1.25rem;
    }
    .reply-item {
        background: var(--surface-subtle2, rgba(0,0,0,0.015));
    }
    .comment-header {
        display: flex;
        align-items: baseline;
        gap: 0.4rem;
        font-size: 0.8rem;
        flex-wrap: wrap;
    }
    .comment-author {
        font-weight: 600;
    }
    .comment-time, .comment-edited {
        font-size: 0.75rem;
    }
    .comment-actions {
        margin-left: auto;
        display: flex;
        gap: 0.3rem;
    }
    .comment-body {
        margin: 0.25rem 0 0.1rem;
        font-size: 0.875rem;
        white-space: pre-wrap;
        word-break: break-word;
    }
    .comment-footer {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.2rem;
    }
    .link-btn {
        background: none;
        border: none;
        padding: 0;
        font-size: 0.75rem;
        color: var(--accent, #6366f1);
        cursor: pointer;
        text-decoration: underline;
    }
    .danger-link {
        color: var(--danger, #ef4444);
    }
    .comment-edit textarea {
        width: 100%;
        resize: vertical;
        font-size: 0.875rem;
        padding: 0.3rem 0.5rem;
    }
    .comment-edit-actions {
        display: flex;
        gap: 0.4rem;
        margin-top: 0.3rem;
    }
    .reply-compose {
        margin-top: 0.4rem;
        margin-left: 1.25rem;
    }
</style>
