import type { Item } from './api';

/**
 * Returns the most contextually relevant secondary line for an item card/row,
 * adapting to the item's category:
 *   - Music → artist (attrs.creator)
 *   - Books → author (attrs.creator)
 *   - Movies / TV → subtitle, then director (attrs.creator)
 *   - Groceries / Home Goods / Hardware → brand (attrs.brand or attrs.creator)
 *   - Default → subtitle, then attrs.creator
 */
export function secondaryLine(item: Item): string {
    const slug = item.category_slug ?? '';
    const root = slug.split('.')[0];
    const creator = item.attrs?.creator ? String(item.attrs.creator) : '';
    const brand   = item.attrs?.brand   ? String(item.attrs.brand)   : '';

    switch (root) {
        case 'music':
            return creator || item.subtitle || '';
        case 'books':
            return creator || item.subtitle || '';
        case 'movies':
        case 'tv':
            return item.subtitle || creator || '';
        case 'groceries':
        case 'home_goods':
        case 'hardware':
            return brand || creator || item.subtitle || '';
        default:
            return item.subtitle || creator || '';
    }
}

/**
 * Returns the label to use for the secondary line in a column header,
 * based on the collection's default category root slug.
 */
export function secondaryLineLabel(defaultCategorySlug: string | null | undefined): string {
    const root = (defaultCategorySlug ?? '').split('.')[0];
    switch (root) {
        case 'music':    return 'Artist';
        case 'books':    return 'Author';
        case 'movies':
        case 'tv':       return 'Subtitle';
        case 'groceries':
        case 'home_goods':
        case 'hardware': return 'Brand';
        default:         return 'Subtitle';
    }
}
