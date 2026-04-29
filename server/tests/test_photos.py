"""Photo upload + EXIF + HEIC tests."""

from __future__ import annotations

import io

from PIL import Image


def _png_bytes(size=(40, 30), color=(200, 80, 20)) -> bytes:
    img = Image.new("RGB", size, color=color)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _jpeg_with_orientation(orientation: int) -> bytes:
    img = Image.new("RGB", (60, 20), color=(0, 100, 200))
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=Image.Exif().tobytes() if False else b"")
    # Build EXIF with the requested orientation tag (0x0112).
    exif = Image.Exif()
    exif[0x0112] = orientation
    out = io.BytesIO()
    img.save(out, format="JPEG", exif=exif.tobytes())
    return out.getvalue()


def _register(client, username, password="hunter22-secure"):
    r = client.post(
        "/auth/register",
        json={"username": username, "password": password, "email": f"{username}@x.io"},
    )
    assert r.status_code == 201, r.text


def _login(client, username, password="hunter22-secure"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text


def _setup_item(client, owner="alice"):
    _register(client, owner)
    _login(client, owner)
    cid = client.post("/collections", json={"name": "Stuff"}).json()["id"]
    iid = client.post(
        "/items", json={"collection_id": cid, "category": "tools.hand", "title": "Drill"}
    ).json()["id"]
    return cid, iid


def test_upload_multiple_photos(client) -> None:
    _, iid = _setup_item(client, "pho")
    files = [
        ("files", ("a.png", io.BytesIO(_png_bytes()), "image/png")),
        ("files", ("b.png", io.BytesIO(_png_bytes(color=(0, 0, 200))), "image/png")),
    ]
    r = client.post(f"/items/{iid}/photos", files=files)
    assert r.status_code == 201, r.text
    photos = r.json()
    assert len(photos) == 2
    assert photos[0]["is_primary"] is True
    assert photos[1]["is_primary"] is False
    assert photos[0]["width"] == 40
    assert photos[0]["height"] == 30


def test_set_primary_photo(client) -> None:
    _, iid = _setup_item(client, "prim")
    client.post(
        f"/items/{iid}/photos",
        files=[("files", ("a.png", io.BytesIO(_png_bytes()), "image/png"))],
    )
    p2 = client.post(
        f"/items/{iid}/photos",
        files=[("files", ("b.png", io.BytesIO(_png_bytes(color=(10, 10, 10))), "image/png"))],
    ).json()[0]

    r = client.patch(f"/photos/{p2['id']}", json={"is_primary": True})
    assert r.status_code == 200
    assert r.json()["is_primary"] is True
    listing = client.get(f"/items/{iid}/photos").json()
    primaries = [p for p in listing if p["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["id"] == p2["id"]


def test_delete_promotes_next_primary(client) -> None:
    _, iid = _setup_item(client, "del")
    files = [
        ("files", ("a.png", io.BytesIO(_png_bytes()), "image/png")),
        ("files", ("b.png", io.BytesIO(_png_bytes(color=(0, 0, 50))), "image/png")),
    ]
    photos = client.post(f"/items/{iid}/photos", files=files).json()
    primary_id = photos[0]["id"]
    other_id = photos[1]["id"]
    r = client.delete(f"/photos/{primary_id}")
    assert r.status_code == 204
    remaining = client.get(f"/items/{iid}/photos").json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == other_id
    assert remaining[0]["is_primary"] is True


def test_exif_rotation_changes_dimensions(client) -> None:
    """Orientation 6 = 90° CCW; transposed image swaps width/height."""
    _, iid = _setup_item(client, "exif")
    raw = _jpeg_with_orientation(6)
    r = client.post(
        f"/items/{iid}/photos",
        files=[("files", ("rot.jpg", io.BytesIO(raw), "image/jpeg"))],
    )
    assert r.status_code == 201, r.text
    photo = r.json()[0]
    # Original 60x20; rotated dimensions should be 20x60.
    assert photo["width"] == 20
    assert photo["height"] == 60


def test_reject_non_image(client) -> None:
    _, iid = _setup_item(client, "bad")
    r = client.post(
        f"/items/{iid}/photos",
        files=[("files", ("x.txt", io.BytesIO(b"not an image"), "image/png"))],
    )
    assert r.status_code == 415


def test_viewer_cannot_upload_photo(client) -> None:
    _register(client, "owner2")
    _register(client, "viewer2")
    _login(client, "owner2")
    cid = client.post("/collections", json={"name": "X"}).json()["id"]
    iid = client.post(
        "/items", json={"collection_id": cid, "category": "other.generic", "title": "Y"}
    ).json()["id"]
    client.post(
        f"/collections/{cid}/members",
        json={"user_identifier": "viewer2", "role": "viewer"},
    )
    client.post("/auth/logout")
    _login(client, "viewer2")
    r = client.post(
        f"/items/{iid}/photos",
        files=[("files", ("a.png", io.BytesIO(_png_bytes()), "image/png"))],
    )
    assert r.status_code == 403
