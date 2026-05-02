"""Metadata scraper tests."""

from __future__ import annotations

import httpx
import pytest

from tangible.services import metadata as md


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


def test_registry_requires_auth(client) -> None:
    r = client.get("/api/metadata/registry")
    assert r.status_code == 401


def test_registry_list_and_import(client) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "registryuser", "password": "hunter22-secure", "email": "r@x.io"},
    )
    client.post(
        "/api/auth/login",
        json={"username": "registryuser", "password": "hunter22-secure"},
    )
    cid = client.post("/api/collections", json={"name": "Library"}).json()["id"]

    listed = client.get("/api/metadata/registry")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
    entry_id = listed.json()[0]["id"]

    imported = client.post(
        "/api/metadata/registry/import",
        json={"collection_id": cid, "entry_ids": [entry_id]},
    )
    assert imported.status_code == 200, imported.text
    assert len(imported.json()) == 1

    # Re-importing the same entry should return the existing template, not duplicate.
    imported_again = client.post(
        "/api/metadata/registry/import",
        json={"collection_id": cid, "entry_ids": [entry_id]},
    )
    assert imported_again.status_code == 200, imported_again.text
    assert imported_again.json()[0]["id"] == imported.json()[0]["id"]


def test_registry_import_requires_editor_role(client) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "owner2", "password": "hunter22-secure", "email": "o2@x.io"},
    )
    client.post(
        "/api/auth/register",
        json={"username": "viewer2", "password": "hunter22-secure", "email": "v2@x.io"},
    )
    client.post("/api/auth/login", json={"username": "owner2", "password": "hunter22-secure"})
    cid = client.post("/api/collections", json={"name": "Shared"}).json()["id"]
    client.post(
        f"/api/collections/{cid}/members",
        json={"user_identifier": "viewer2", "role": "viewer"},
    )
    client.post("/api/auth/logout")

    client.post("/api/auth/login", json={"username": "viewer2", "password": "hunter22-secure"})
    denied = client.post(
        "/api/metadata/registry/import",
        json={"collection_id": cid, "entry_ids": ["openlibrary-books"]},
    )
    assert denied.status_code == 403


def test_registry_admin_can_pin_trust(client) -> None:
    # First registered user is admin.
    registered = client.post(
        "/api/auth/register",
        json={"username": "adminpin", "password": "hunter22-secure", "email": "ap@x.io"},
    )
    assert registered.status_code == 201, registered.text
    assert registered.json()["is_admin"] is True
    client.post(
        "/api/auth/login",
        json={"username": "adminpin", "password": "hunter22-secure"},
    )

    patched = client.patch(
        "/api/metadata/registry/openlibrary-books/trust",
        json={"trusted": False},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["id"] == "openlibrary-books"
    assert patched.json()["trusted"] is False

    listed = client.get("/api/metadata/registry")
    assert listed.status_code == 200, listed.text
    by_id = {entry["id"]: entry for entry in listed.json()}
    assert by_id["openlibrary-books"]["trusted"] is False


def test_registry_pin_requires_admin(client) -> None:
    # Bootstrap first-user admin, then create a non-admin user for denial check.
    client.post(
        "/api/auth/register",
        json={"username": "firstadmin", "password": "hunter22-secure", "email": "fa@x.io"},
    )
    client.post("/api/auth/logout")

    client.post(
        "/api/auth/register",
        json={"username": "normalpin", "password": "hunter22-secure", "email": "np@x.io"},
    )
    client.post(
        "/api/auth/login",
        json={"username": "normalpin", "password": "hunter22-secure"},
    )
    denied = client.patch(
        "/api/metadata/registry/openlibrary-books/trust",
        json={"trusted": False},
    )
    assert denied.status_code == 403


# ---------------------------------------------------------------------------
# Plugin adapter tests
# ---------------------------------------------------------------------------


def test_register_barcode_adapter_prepends() -> None:
    """register_barcode_adapter() inserts the new adapter at index 0."""
    orig = md._BARCODE_ADAPTERS[:]

    class _FakeBarcodeAdapter:
        name = "test_barcode_prepend"

        def lookup(self, barcode: str, *, client) -> list[md.ScrapeResult]:
            return []

    adapter = _FakeBarcodeAdapter()
    try:
        md.register_barcode_adapter(adapter)
        assert md._BARCODE_ADAPTERS[0] is adapter
        assert md._BARCODE_ADAPTERS[0].name == "test_barcode_prepend"
    finally:
        md._BARCODE_ADAPTERS[:] = orig


def test_list_adapters_returns_names() -> None:
    """list_adapters() returns dicts of adapter names for url and barcode."""
    info = md.list_adapters()
    assert "url" in info
    assert "barcode" in info
    assert "opengraph" in info["url"]
    assert "openlibrary" in info["barcode"]


def test_discover_plugins_registers_via_entry_points(monkeypatch) -> None:
    """discover_plugins() loads entry-point classes and registers them."""
    import importlib.metadata

    class _FakeUrlAdapter:
        name = "fake_plugin_url"

        def matches(self, url: str) -> bool:
            return "fake.example" in url

        def fetch(self, url: str, *, client) -> md.ScrapeResult:
            return md.ScrapeResult(provider="fake_plugin_url", url=url, title="Fake")

    class _FakeBarcodeAdapter:
        name = "fake_plugin_barcode"

        def lookup(self, barcode: str, *, client) -> list[md.ScrapeResult]:
            return []

    class _FakeEP:
        def __init__(self, name, cls):
            self.name = name
            self._cls = cls

        def load(self):
            return self._cls

    def _mock_eps(*, group):
        if group == "tangible.scraper_adapter":
            return [_FakeEP("fake-url", _FakeUrlAdapter)]
        if group == "tangible.barcode_adapter":
            return [_FakeEP("fake-barcode", _FakeBarcodeAdapter)]
        return []

    monkeypatch.setattr(importlib.metadata, "entry_points", _mock_eps)

    orig_adapters = md._ADAPTERS[:]
    orig_barcode = md._BARCODE_ADAPTERS[:]
    try:
        md.discover_plugins()
        assert md._ADAPTERS[0].name == "fake_plugin_url"
        assert md._BARCODE_ADAPTERS[0].name == "fake_plugin_barcode"
    finally:
        md._ADAPTERS[:] = orig_adapters
        md._BARCODE_ADAPTERS[:] = orig_barcode


def test_discover_plugins_skips_broken_entry_point(monkeypatch) -> None:
    """discover_plugins() logs a warning and skips adapters that fail to load."""
    import importlib.metadata

    class _BrokenEP:
        name = "broken"

        def load(self):
            raise ImportError("no such module")

    monkeypatch.setattr(
        importlib.metadata, "entry_points",
        lambda *, group: [_BrokenEP()] if group == "tangible.scraper_adapter" else [],
    )

    orig = md._ADAPTERS[:]
    try:
        md.discover_plugins()  # must not raise
        assert orig == md._ADAPTERS  # nothing registered
    finally:
        md._ADAPTERS[:] = orig


def test_adapters_endpoint_requires_admin(client) -> None:
    r = client.get("/api/metadata/adapters")
    assert r.status_code == 401


def test_adapters_endpoint_returns_adapter_names(client) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "adaptersadmin", "password": "hunter22-secure", "email": "aa@x.io"},
    )
    client.post("/api/auth/login", json={"username": "adaptersadmin", "password": "hunter22-secure"})

    r = client.get("/api/metadata/adapters")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "url" in body
    assert "barcode" in body
    assert "opengraph" in body["url"]
    assert "openlibrary" in body["barcode"]
