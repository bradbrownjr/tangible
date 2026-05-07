<script lang="ts">
    import ShoppingStoreManager from '$lib/ShoppingStoreManager.svelte';
    import { _ } from 'svelte-i18n';
</script>

<svelte:head>
    <title>Tangible · {$_('nav.stores')}</title>
</svelte:head>

<ShoppingStoreManager standalone={true} />
