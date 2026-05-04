export interface ShoppingCategory {
    slug: string;
    label: string;
}

export const GROCERY_CATEGORIES: ShoppingCategory[] = [
    { slug: 'alcohol',            label: 'Alcohol' },
    { slug: 'bakery',             label: 'Bakery' },
    { slug: 'beverages',          label: 'Beverages' },
    { slug: 'bread',              label: 'Bread' },
    { slug: 'breakfast-cereal',   label: 'Breakfast & Cereal' },
    { slug: 'canned-pantry',      label: 'Canned & Pantry' },
    { slug: 'cleaning-household', label: 'Cleaning & Household' },
    { slug: 'condiments-spices',  label: 'Condiments & Spices' },
    { slug: 'dairy-eggs',         label: 'Dairy & Eggs' },
    { slug: 'deli',               label: 'Deli' },
    { slug: 'frozen',             label: 'Frozen' },
    { slug: 'health-beauty',      label: 'Health & Beauty' },
    { slug: 'meat-seafood',       label: 'Meat & Seafood' },
    { slug: 'pasta-grains',       label: 'Pasta & Grains' },
    { slug: 'pet-supplies',       label: 'Pet Supplies' },
    { slug: 'produce',            label: 'Produce' },
    { slug: 'snacks',             label: 'Snacks' },
];

export const HARDWARE_CATEGORIES: ShoppingCategory[] = [
    { slug: 'adhesives-tape',         label: 'Adhesives & Tape' },
    { slug: 'caulk-sealant',          label: 'Caulk & Sealant' },
    { slug: 'concrete-masonry',       label: 'Concrete & Masonry' },
    { slug: 'electrical',             label: 'Electrical' },
    { slug: 'fasteners',              label: 'Fasteners' },
    { slug: 'flooring',               label: 'Flooring' },
    { slug: 'hand-tools',             label: 'Hand Tools' },
    { slug: 'hardware-hinges',        label: 'Hardware & Hinges' },
    { slug: 'hvac-filters',           label: 'HVAC & Filters' },
    { slug: 'lumber-sheet-goods',     label: 'Lumber & Sheet Goods' },
    { slug: 'paint-finishes',         label: 'Paint & Finishes' },
    { slug: 'plumbing',               label: 'Plumbing' },
    { slug: 'power-tool-accessories', label: 'Power Tool Accessories' },
    { slug: 'safety-ppe',             label: 'Safety & PPE' },
    { slug: 'storage-organization',   label: 'Storage & Organization' },
];

export const HOME_GOODS_CATEGORIES: ShoppingCategory[] = [
    { slug: 'bathroom',           label: 'Bathroom' },
    { slug: 'bedding-pillows',    label: 'Bedding & Pillows' },
    { slug: 'candles-fragrance',  label: 'Candles & Fragrance' },
    { slug: 'cleaning-supplies',  label: 'Cleaning Supplies' },
    { slug: 'cookware-bakeware',  label: 'Cookware & Bakeware' },
    { slug: 'curtains-blinds',    label: 'Curtains & Blinds' },
    { slug: 'decor-accents',      label: 'Decor & Accents' },
    { slug: 'furniture',          label: 'Furniture' },
    { slug: 'kitchen-gadgets',    label: 'Kitchen Gadgets' },
    { slug: 'lighting',           label: 'Lighting' },
    { slug: 'linens-towels',      label: 'Linens & Towels' },
    { slug: 'outdoor-garden',     label: 'Outdoor & Garden' },
    { slug: 'rugs-mats',          label: 'Rugs & Mats' },
    { slug: 'small-appliances',   label: 'Small Appliances' },
    { slug: 'storage',            label: 'Storage' },
];

/** Returns the category preset list for a given list type. */
export function categoriesForType(listType: string): ShoppingCategory[] {
    switch (listType) {
        case 'hardware':   return HARDWARE_CATEGORIES;
        case 'home_goods': return HOME_GOODS_CATEGORIES;
        default:           return GROCERY_CATEGORIES;
    }
}
