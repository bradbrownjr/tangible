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
