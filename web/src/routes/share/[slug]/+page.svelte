<script lang="ts">
    import { onMount } from 'svelte';
    import { page } from '$app/state';
    import { _ } from 'svelte-i18n';
    import { api, type Collection, type Item } from '$lib/api';
    import { SectionCard, Badge, EmptyState } from '$lib/components';

    let collection = $state<Collection | null>(null);
    let items = $state<Item[]>([]);
    let loading = $state(true);
    let error = $state('');

    const slug = $derived(page.params.slug ?? '');

    async function load() {
        loading = true;
        try {
            collection = await api.get<Collection>(`/public/share/${slug}`);
            items = await api.get<Item[]>(`/public/share/${slug}/items`);
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    onMount(load);
</script>

{#if loading}
    <EmptyState icon="loader" heading={$_('common.loading')} />
{:else if error}
    <EmptyState icon="share-2" heading={$_('share.not_available')} body={error}>
        <p class="muted">{$_('share.expired_message')}</p>
    </EmptyState>
{:else if collection}
    <SectionCard title={collection.name} description={collection.description ?? undefined}>
        {#snippet actions()}
            <Badge variant="info">{$_('share.read_only_note')}</Badge>
        {/snippet}

        {#if items.length === 0}
            <EmptyState icon="package" heading={$_('share.no_items')} />
        {:else}
            <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>{$_('collection.col_category')}</th>
                        <th>{$_('collection.col_title')}</th>
                        <th>{$_('collection.col_qty')}</th>
                        <th>{$_('collection.col_condition')}</th>
                    </tr>
                </thead>
                <tbody>
                    {#each items as i (i.id)}
                        <tr>
                            <td class="muted">{i.category_slug ?? ''}</td>
                            <td>
                                {i.title}{#if i.subtitle}
                                    <span class="muted">— {i.subtitle}</span>
                                {/if}
                            </td>
                            <td>{i.quantity}</td>
                            <td>{i.condition ?? ''}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
            </div>
        {/if}
    </SectionCard>
{/if}
