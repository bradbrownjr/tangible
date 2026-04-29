"""Metadata scraper tests."""

from __future__ import annotations

import httpx
import pytest

from covet.services import metadata as md


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport, headers={"User-Agent": md.USER_AGENT})


def test_opengraph_extracts_title_image_description() -> None:
    html = b"""
    <html><head>
      <title>Fallback Title</title>
      <meta property="og:title" content="OG Title">
      <meta property="og:description" content="A description.">
      <meta property="og:image" content="https://example.com/cover.jpg">
    </head></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html, headers={"content-type": "text/html"})

    with _make_client(handler) as client:
        result = md.OpenGraphAdapter().fetch(
            "https://example.com/x", client=client
        )
    assert result.title == "OG Title"
    assert result.description == "A description."
    assert result.image_url == "https://example.com/cover.jpg"


def test_opengraph_falls_back_to_title_tag() -> None:
    html = b"<html><head><title>Just Title</title></head></html>"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=html, headers={"content-type": "text/html"})

    with _make_client(handler) as client:
        result = md.OpenGraphAdapter().fetch(
            "https://example.com/y", client=client
        )
    assert result.title == "Just Title"
    assert result.image_url is None


def test_opengraph_rejects_non_html() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"{}", headers={"content-type": "application/json"}
        )

    with _make_client(handler) as client, pytest.raises(md.ScrapeError):
        md.OpenGraphAdapter().fetch("https://example.com/z", client=client)


def test_open_library_isbn_adapter() -> None:
    payload = {
        "ISBN:9780441172719": {
            "title": "Dune",
            "authors": [{"name": "Frank Herbert"}],
            "cover": {"medium": "https://covers.openlibrary.org/b/id/123-M.jpg"},
            "number_of_pages": 658,
            "publish_date": "1965",
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "openlibrary.org/api/books" in str(request.url)
        return httpx.Response(200, json=payload)

    with _make_client(handler) as client:
        result = md.OpenLibraryAdapter().fetch(
            "https://openlibrary.org/isbn/9780441172719", client=client
        )
    assert result.title == "Dune"
    assert result.item_type == "book"
    assert result.attrs["pages"] == 658
    assert result.attrs["isbn"] == "9780441172719"


def test_validate_url_rejects_loopback(monkeypatch) -> None:
    with pytest.raises(md.ScrapeError):
        md.validate_url("http://127.0.0.1/foo")
    with pytest.raises(md.ScrapeError):
        md.validate_url("file:///etc/passwd")
    with pytest.raises(md.ScrapeError):
        md.validate_url("https:///no-host")


def test_scrape_endpoint_requires_auth(client) -> None:
    r = client.post("/api/metadata/scrape", json={"url": "https://example.com"})
    assert r.status_code == 401


def test_scrape_endpoint_rejects_loopback(client, monkeypatch) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "scraper", "password": "hunter22-secure", "email": "s@x.io"},
    )
    client.post("/api/auth/login", json={"username": "scraper", "password": "hunter22-secure"})
    r = client.post("/api/metadata/scrape", json={"url": "http://127.0.0.1/x"})
    assert r.status_code == 400
