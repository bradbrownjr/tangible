"""Seed catalog of curated item categories.

Loaded by Alembic migration ``0008_categories``. Two-level tree: roots
(e.g. ``music``) and leaves (e.g. ``music.vinyl``). Slugs are dotted.

Sources informing the taxonomy:
- Discogs catalog guidelines (music format vocabulary).
- BoardGameGeek subdomains (Board / Card / RPG / Miniatures split).
- IGDB / LaunchBox platform list (video-game console set).
"""

from __future__ import annotations

from typing import TypedDict


class CategorySeed(TypedDict, total=False):
    slug: str
    name: str
    description: str
    children: list[CategorySeed]


CATEGORY_TREE: list[CategorySeed] = [
    {
        "slug": "music",
        "name": "Music",
        "description": "Recorded music in any format.",
        "children": [
            {"slug": "music.vinyl", "name": "Vinyl",
             "description": "LPs, EPs, 7\" / 10\" / 12\" records."},
            {"slug": "music.cd", "name": "Compact Disc"},
            {"slug": "music.sacd", "name": "SACD",
             "description": "Super Audio CD — high-resolution successor to CD."},
            {"slug": "music.cassette", "name": "Cassette"},
            {"slug": "music.minidisc", "name": "MiniDisc"},
            {"slug": "music.eight_track", "name": "8-Track"},
            {"slug": "music.reel", "name": "Reel-to-Reel"},
            {"slug": "music.digital", "name": "Digital",
             "description": "FLAC / MP3 / AAC files, DRM-free or platform-bound."},
        ],
    },
    {
        "slug": "movies",
        "name": "Movies",
        "description": "Films and other long-form video on physical or digital media.",
        "children": [
            {"slug": "movies.vhs", "name": "VHS"},
            {"slug": "movies.betamax", "name": "Betamax"},
            {"slug": "movies.laserdisc", "name": "LaserDisc"},
            {"slug": "movies.vcd", "name": "VCD / SVCD",
             "description": "Video CD and the higher-rate Super VCD variant."},
            {"slug": "movies.dvd", "name": "DVD"},
            {"slug": "movies.hddvd", "name": "HD-DVD"},
            {"slug": "movies.bluray", "name": "Blu-ray"},
            {"slug": "movies.uhd", "name": "4K Ultra HD Blu-ray"},
            {"slug": "movies.digital", "name": "Digital",
             "description": "Movies Anywhere, iTunes, Vudu, Plex local files, etc."},
        ],
    },
    {
        "slug": "games",
        "name": "Video Games",
        "description": "Console / handheld / PC games and the hardware to play them.",
        "children": [
            {"slug": "games.software", "name": "Game",
             "description": "A single title (cartridge, disc, or digital)."},
            {"slug": "games.console", "name": "Console / Hardware",
             "description": "A console or handheld system. Link games to it as children."},
            {"slug": "games.peripheral", "name": "Peripheral",
             "description": "Controllers, memory cards, light guns, etc."},
        ],
    },
    {
        "slug": "tabletop",
        "name": "Tabletop",
        "description": "Board games, card games, RPGs, and miniatures.",
        "children": [
            {"slug": "tabletop.board_game", "name": "Board Game"},
            {"slug": "tabletop.card_game", "name": "Card Game",
             "description": "Standard, deck-building, and collectible (CCG/TCG)."},
            {"slug": "tabletop.rpg_book", "name": "RPG Book",
             "description": "Rulebooks, sourcebooks, modules."},
            {"slug": "tabletop.miniatures", "name": "Miniatures"},
            {"slug": "tabletop.dice_accessories", "name": "Dice / Accessories"},
        ],
    },
    {
        "slug": "books",
        "name": "Books",
        "description": "Print and digital reading material.",
        "children": [
            {"slug": "books.print", "name": "Book",
             "description": "Hardcover, paperback, or trade."},
            {"slug": "books.comic", "name": "Comic / Graphic Novel"},
            {"slug": "books.magazine", "name": "Magazine / Periodical"},
            {"slug": "books.ebook", "name": "E-Book"},
        ],
    },
    {
        "slug": "collectibles",
        "name": "Collectibles",
        "description": "Toys, figures, trading cards, memorabilia.",
        "children": [
            {"slug": "collectibles.funko", "name": "Funko Pop"},
            {"slug": "collectibles.trading_card", "name": "Trading Card",
             "description": "Sports, Pokémon, Magic, etc. Track grade and slab."},
            {"slug": "collectibles.action_figure", "name": "Action Figure"},
            {"slug": "collectibles.plush", "name": "Plush"},
            {"slug": "collectibles.memorabilia", "name": "Memorabilia"},
        ],
    },
    {
        "slug": "tools",
        "name": "Tools",
        "description": "Hand tools, power tools, shop equipment.",
        "children": [
            {"slug": "tools.hand", "name": "Hand Tool"},
            {"slug": "tools.power", "name": "Power Tool"},
            {"slug": "tools.shop", "name": "Shop Equipment"},
        ],
    },
    {
        "slug": "spices",
        "name": "Pantry",
        "description": "Pantry inventory with shelf-life tracking.",
        "children": [
            {"slug": "spices.spice", "name": "Spice"},
            {"slug": "spices.pantry", "name": "Pantry Item"},
        ],
    },
    {
        "slug": "home_equipment",
        "name": "Home Equipment",
        "description": "Appliances and household infrastructure.",
        "children": [
            {"slug": "home_equipment.appliance", "name": "Appliance"},
            {"slug": "home_equipment.generator", "name": "Generator"},
            {"slug": "home_equipment.hvac", "name": "HVAC / Furnace / Air Handler"},
            {"slug": "home_equipment.water_heater", "name": "Water Heater"},
            {"slug": "home_equipment.refrigerator", "name": "Refrigerator"},
            {"slug": "home_equipment.water_filtration", "name": "Water Service Filtration"},
            {"slug": "home_equipment.sump_pump", "name": "Sump Pump"},
        ],
    },
    {
        "slug": "fuel_chemicals",
        "name": "Fuel & Chemicals",
        "description": "Stored fuels, lubricants, and household/shop chemicals.",
        "children": [
            {"slug": "fuel_chemicals.stored_fuel", "name": "Stored Fuel"},
            {"slug": "fuel_chemicals.lubricants_fluids", "name": "Lubricants & Fluids"},
            {"slug": "fuel_chemicals.chemicals_cleaning", "name": "Chemicals & Cleaning"},
        ],
    },
    {
        "slug": "vehicles",
        "name": "Vehicles",
        "description": "Road, outdoor, and recreational vehicles/equipment.",
        "children": [
            {"slug": "vehicles.car_truck_suv", "name": "Car / Truck / SUV"},
            {"slug": "vehicles.motorcycle_atv_utv", "name": "Motorcycle / ATV / UTV"},
            {"slug": "vehicles.lawn_garden_equipment", "name": "Lawn & Garden Equipment"},
            {"slug": "vehicles.boat_pwc", "name": "Boat / PWC"},
            {"slug": "vehicles.trailer", "name": "Trailer"},
            {"slug": "vehicles.bicycle_ebike", "name": "Bicycle / E-Bike"},
        ],
    },
    {
        "slug": "batteries",
        "name": "Batteries",
        "description": "Rechargeable and disposable batteries, including specialized types.",
        "children": [
            {"slug": "batteries.rechargeable", "name": "Rechargeable Battery"},
            {"slug": "batteries.disposable", "name": "Disposable Battery"},
            {"slug": "batteries.smoke_detector", "name": "Smoke Detector Battery Program"},
        ],
    },
    {
        "slug": "clothing",
        "name": "Clothing & Wardrobe",
        "description": "Apparel, footwear, and fashion accessories.",
        "children": [
            {"slug": "clothing.clothing_item", "name": "Clothing Item"},
            {"slug": "clothing.footwear", "name": "Footwear"},
            {"slug": "clothing.accessories", "name": "Accessories"},
        ],
    },
    {
        "slug": "art_decor",
        "name": "Art & Décor",
        "description": "Artwork, framed prints, decorative objects.",
        "children": [
            {"slug": "art_decor.artwork", "name": "Artwork"},
            {"slug": "art_decor.framed_print", "name": "Framed Print / Poster"},
            {"slug": "art_decor.decorative_object", "name": "Decorative Object"},
        ],
    },
    {
        "slug": "sports",
        "name": "Sports & Recreation",
        "description": "Fitness, outdoor, and recreational sports equipment.",
        "children": [
            {"slug": "sports.fitness", "name": "Fitness Equipment"},
            {"slug": "sports.outdoor", "name": "Outdoor Gear"},
            {"slug": "sports.sports_equipment", "name": "Sports Equipment"},
        ],
    },
    {
        "slug": "other",
        "name": "Other",
        "description": "Anything not covered above.",
        "children": [
            {"slug": "other.generic", "name": "Generic"},
        ],
    },
]


def iter_seed_rows() -> list[dict[str, str | int | None]]:
    """Flatten the tree into rows ready for bulk-insert."""
    out: list[dict[str, str | int | None]] = []
    for root_pos, root in enumerate(CATEGORY_TREE):
        out.append({
            "slug": root["slug"],
            "parent_slug": None,
            "name": root["name"],
            "description": root.get("description"),
            "position": root_pos,
        })
        for leaf_pos, leaf in enumerate(root.get("children", [])):
            out.append({
                "slug": leaf["slug"],
                "parent_slug": root["slug"],
                "name": leaf["name"],
                "description": leaf.get("description"),
                "position": leaf_pos,
            })
    return out


# Convenient default: where new items land if no category is chosen.
DEFAULT_LEAF_SLUG = "other.generic"
