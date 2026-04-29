<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { api, type InvitationPreview } from '$lib/api';
    import { me } from '$lib/session';

    let preview = $state<InvitationPreview | null>(null);
    let loading = $state(true);
    let error = $state('');
    let accepting = $state(false);

    const token = $derived($page.params.token ?? '');

    async function load() {
        loading = true;
        try {
            preview = await api.get<InvitationPreview>(`/invitations/${token}`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    async function accept() {
        accepting = true;
        try {
            await api.post(`/invitations/${token}/accept`);
            await goto(`/collections/${preview!.collection_id}`);
        } catch (e) {
            error = (e as Error).message;
            accepting = false;
        }
    }

    onMount(load);
</script>

<h1>Collection invitation</h1>

{#if loading}
    <p class="muted">Loading…</p>
{:else if error}
    <p class="error">{error}</p>
    <p class="muted">This invitation may be expired or revoked.</p>
{:else if preview}
    <div class="card">
        <p>
            You've been invited to join
            <strong>{preview.collection_name}</strong>
            as <strong>{preview.role}</strong>.
        </p>

        {#if $me}
            <p class="muted">Signed in as {$me.username}.</p>
            <button onclick={accept} disabled={accepting}>
                {accepting ? 'Accepting…' : 'Accept invitation'}
            </button>
        {:else}
            <p>You'll need to sign in or create an account to accept.</p>
            <a href="/login?next={encodeURIComponent(`/invite/${token}`)}">Sign in</a>
            ·
            <a href="/register">Create an account</a>
        {/if}
    </div>
{/if}
