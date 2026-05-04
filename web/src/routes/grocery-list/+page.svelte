<!-- Redirect to the new unified lists route -->
<script lang="ts">
    import { goto } from '$app/navigation';
    import { onMount } from 'svelte';
    onMount(() => goto('/lists/groceries', { replaceState: true }));
</script>
