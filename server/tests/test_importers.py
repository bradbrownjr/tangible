"""Unit tests for the importer parsers (no DB)."""

from __future__ import annotations

import io

from covet.importers import (
    CLZBookImporter,
    CLZComicImporter,
    CLZGameImporter,
    CLZMovieImporter,
    CLZMusicImporter,
    CSVImporter,
)


def test_clz_movie_basic_parse() -> None:
    xml = b"""<?xml version="1.0"?>
<movielist>
    <movie>
        <title>The Matrix</title>
        <year>1999</year>
        <runtime>136</runtime>
        <format>Blu-ray</format>
        <barcode>012345678901</barcode>
        <genres>
            <genre><displayname>Action</displayname></genre>
            <genre><displayname>SciFi</displayname></genre>
        </genres>
        <actors>
            <actor><displayname>Keanu Reeves</displayname></actor>
        </actors>
        <notes>Director's cut</notes>
        <quantity>1</quantity>
    </movie>
    <movie>
        <title>Blade Runner</title>
        <year>1982</year>
    </movie>
</movielist>"""
    result = CLZMovieImporter().parse(io.BytesIO(xml))
    assert result.warnings == []
    assert len(result.items) == 2
    matrix = result.items[0]
    assert matrix.category_slug == "movies.dvd"
    assert matrix.title == "The Matrix"
    assert matrix.identifiers["barcode"] == "012345678901"
    assert matrix.attrs["year"] == "1999"
    assert matrix.attrs["genres"] == ["Action", "SciFi"]
    assert matrix.attrs["actors"] == ["Keanu Reeves"]
    assert matrix.attrs["runtime"] == "136"
    assert matrix.notes == "Director's cut"


def test_clz_music_book_comic_game() -> None:
    cases = [
        (
            CLZMusicImporter(),
            b"<musiclist><music><title>OK Computer</title><artist>Radiohead</artist></music></musiclist>",
            {"title": "OK Computer", "category": "music.cd", "artist": "Radiohead"},
        ),
        (
            CLZBookImporter(),
            b"<booklist><book><title>Dune</title><author>Frank Herbert</author><isbn>9780441172719</isbn></book></booklist>",
            {"title": "Dune", "category": "books.print", "author": "Frank Herbert", "isbn": "9780441172719"},
        ),
        (
            CLZComicImporter(),
            b"<comiclist><comic><title>Saga #1</title><series>Saga</series><issuenr>1</issuenr></comic></comiclist>",
            {"title": "Saga #1", "category": "books.comic", "series": "Saga"},
        ),
        (
            CLZGameImporter(),
            b"<gamelist><game><title>Hades</title><platform>Switch</platform></game></gamelist>",
            {"title": "Hades", "category": "games.software", "platform": "Switch"},
        ),
    ]
    for importer, xml, expected in cases:
        result = importer.parse(io.BytesIO(xml))
        assert len(result.items) == 1, f"{importer.name}: no items"
        item = result.items[0]
        assert item.title == expected["title"]
        assert item.category_slug == expected["category"]
        for key, value in expected.items():
            if key in ("title", "category"):
                continue
            if key in item.identifiers:
                assert item.identifiers[key] == value
            else:
                assert item.attrs.get(key) == value, f"{importer.name}: {key}"


def test_clz_warns_on_wrong_kind() -> None:
    result = CLZMovieImporter().parse(
        io.BytesIO(b"<musiclist><music><title>X</title></music></musiclist>")
    )
    assert result.items == []
    assert any("No <movie>" in w for w in result.warnings)


def test_csv_importer_with_mapping() -> None:
    csv_text = (
        b"Name,Year,Barcode,Genre,Notes\n"
        b"The Matrix,1999,012345,Action,Great\n"
        b"Blade Runner,1982,067890,SciFi,Classic\n"
        b",2020,000,Drama,Missing title\n"  # dropped: no title
    )
    importer = CSVImporter(
        category_slug="movies.dvd",
        mapping={
            "Name": "title",
            "Year": "attr:year",
            "Barcode": "id:barcode",
            "Genre": "attr:genre",
            "Notes": "notes",
        },
    )
    result = importer.parse(io.BytesIO(csv_text))
    assert len(result.items) == 2
    first = result.items[0]
    assert first.title == "The Matrix"
    assert first.identifiers["barcode"] == "012345"
    assert first.attrs["year"] == "1999"
    assert first.notes == "Great"


def test_csv_importer_warns_on_unknown_column() -> None:
    csv_text = b"title,extra\nFoo,Bar\n"
    importer = CSVImporter(category_slug="other.generic", mapping={"title": "title"})
    result = importer.parse(io.BytesIO(csv_text))
    assert len(result.items) == 1
    assert any("Ignoring unmapped" in w for w in result.warnings)
