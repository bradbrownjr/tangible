<!-- Responsive data table.
     - Desktop (>=640px): standard <table> with sortable column headers.
     - Mobile (<640px): card-per-row layout using the `mobileLabel` from each column.

     Usage:
       <script lang="ts">
         import DataTable from '$lib/components/DataTable.svelte';
         import type { Column } from '$lib/components/DataTable.svelte';

         type Item = { id: number; name: string; qty: number };
         const cols: Column<Item>[] = [
             { key: 'name', label: 'Name', sortable: true },
             { key: 'qty',  label: 'Qty',  sortable: true, align: 'right' },
         ];
         let rows = $state<Item[]>([...]);
       </script>
       <DataTable {cols} {rows} rowKey="id" />
-->
<script lang="ts" generics="T extends Record<string, unknown>">
    import type { Snippet } from 'svelte';
    import type { Column } from './data-table-types.js';

    interface Props {
        cols: Column<T>[];
        rows: T[];
        rowKey?: keyof T & string;
        /** Initial sort column key */
        sortKey?: string;
        sortDir?: 'asc' | 'desc';
        /** Emitted when user clicks a sortable header */
        onsort?: (key: string, dir: 'asc' | 'desc') => void;
        /** Renders extra actions per row (e.g. edit/delete buttons) */
        actions?: Snippet<[T]>;
        /** Replaces the entire empty state */
        empty?: Snippet;
        loading?: boolean;
        class?: string;
    }

    let {
        cols,
        rows,
        rowKey,
        sortKey = $bindable(''),
        sortDir = $bindable('asc'),
        onsort,
        actions,
        empty,
        loading = false,
        class: cls = '',
    }: Props = $props();

    function toggleSort(key: string) {
        if (sortKey === key) {
            sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        } else {
            sortKey = key;
            sortDir = 'asc';
        }
        onsort?.(sortKey, sortDir);
    }

    function cellValue(row: T, key: string): unknown {
        return row[key];
    }
</script>

<div class="dt-wrapper {cls}">
    {#if loading}
        <div class="dt-loading" aria-busy="true" aria-label="Loading">
            <span class="dt-spinner"></span>
        </div>
    {:else if rows.length === 0}
        {#if empty}
            {@render empty()}
        {:else}
            <p class="dt-empty muted">No records found.</p>
        {/if}
    {:else}
        <!-- Desktop table -->
        <div class="dt-scroll">
            <table class="dt-table">
                <thead>
                    <tr>
                        {#each cols as col (col.key)}
                            <th
                                class={[col.tdClass, col.align === 'right' && 'dt-th--right', col.align === 'center' && 'dt-th--center', col.sortable && 'dt-th--sortable'].filter(Boolean).join(' ')}
                                onclick={col.sortable ? () => toggleSort(col.key) : undefined}
                                aria-sort={col.sortable && sortKey === col.key
                                    ? sortDir === 'asc' ? 'ascending' : 'descending'
                                    : undefined}
                            >
                                {col.label}
                                {#if col.sortable && sortKey === col.key}
                                    <span class="dt-sort-icon" aria-hidden="true">
                                        {sortDir === 'asc' ? '↑' : '↓'}
                                    </span>
                                {/if}
                            </th>
                        {/each}
                        {#if actions}<th class="dt-th--actions"></th>{/if}
                    </tr>
                </thead>
                <tbody>
                    {#each rows as row (rowKey ? row[rowKey] : row)}
                        <tr id={rowKey ? `item-${row[rowKey]}` : undefined}>
                            {#each cols as col (col.key)}
                                <td
                                    class={[col.tdClass, col.align === 'right' && 'dt-td--right', col.align === 'center' && 'dt-td--center'].filter(Boolean).join(' ')}
                                >
                                    {#if col.cell}
                                        {@render col.cell(row)}
                                    {:else}
                                        {cellValue(row, col.key) ?? ''}
                                    {/if}
                                </td>
                            {/each}
                            {#if actions}
                                <td class="dt-td--actions">{@render actions(row)}</td>
                            {/if}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <!-- Mobile cards -->
        <ul class="dt-cards">
            {#each rows as row (rowKey ? row[rowKey] : row)}
                <li class="dt-card card" id={rowKey ? `item-${row[rowKey]}` : undefined}>
                    {#each cols as col (col.key)}
                        <div class="dt-card__row">
                            <span class="dt-card__label">
                                {col.mobileLabel ?? col.label}
                            </span>
                            <span class="dt-card__value">
                                {#if col.cell}
                                    {@render col.cell(row)}
                                {:else}
                                    {cellValue(row, col.key) ?? ''}
                                {/if}
                            </span>
                        </div>
                    {/each}
                    {#if actions}
                        <div class="dt-card__actions">{@render actions(row)}</div>
                    {/if}
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    /* Desktop table — hidden on mobile */
    .dt-scroll { overflow-x: auto; }
    .dt-table { width: 100%; border-collapse: collapse; }
    .dt-th--sortable { cursor: pointer; user-select: none; }
    .dt-th--sortable:hover { color: var(--accent); }
    .dt-th--right, .dt-td--right { text-align: right; }
    .dt-th--center, .dt-td--center { text-align: center; }
    .dt-th--actions, .dt-td--actions { width: 1px; white-space: nowrap; }
    .dt-td--actions { display: flex; gap: var(--space-1); align-items: center; }
    .dt-sort-icon { margin-left: var(--space-1); font-size: var(--text-xs); }

    /* Mobile cards — hidden on desktop */
    .dt-cards {
        display: none;
        list-style: none;
        margin: 0;
        padding: 0;
        flex-direction: column;
        gap: var(--space-3);
    }
    .dt-card { padding: var(--space-3) var(--space-4); }
    .dt-card__row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: var(--space-3);
        padding: var(--space-1) 0;
        border-bottom: 1px solid var(--border);
        font-size: var(--text-sm);
    }
    .dt-card__row:last-of-type { border-bottom: none; }
    .dt-card__label { color: var(--text-muted); font-size: var(--text-xs); white-space: nowrap; }
    .dt-card__value { text-align: right; }
    .dt-card__actions {
        display: flex;
        gap: var(--space-2);
        justify-content: flex-end;
        margin-top: var(--space-3);
        padding-top: var(--space-2);
        border-top: 1px solid var(--border);
    }

    /* Breakpoint: ≤640px → show cards, hide table */
    @media (max-width: 640px) {
        .dt-scroll { display: none; }
        .dt-cards  { display: flex; }
    }

    /* Loading + empty */
    .dt-loading {
        display: flex;
        justify-content: center;
        padding: var(--space-7);
    }
    .dt-spinner {
        width: 2rem;
        height: 2rem;
        border: 3px solid var(--border);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .dt-empty {
        text-align: center;
        padding: var(--space-7);
        margin: 0;
    }
</style>
