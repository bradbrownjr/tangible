"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangible.config import Settings, reset_settings_cache


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_settings_cache()


def test_sqlite_default_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TANGIBLE_DATA_DIR", str(tmp_path))
    s = Settings()
    assert s.resolved_database_url() == f"sqlite:///{tmp_path / 'tangible.db'}"


def test_postgres_assembly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TANGIBLE_DB_TYPE", "postgresql")
    monkeypatch.setenv("TANGIBLE_DB_HOST", "db.example.com")
    monkeypatch.setenv("TANGIBLE_DB_USER", "tangible")
    monkeypatch.setenv("TANGIBLE_DB_PASSWORD", "secret")
    monkeypatch.setenv("TANGIBLE_DB_NAME", "tangible")
    s = Settings()
    assert s.resolved_database_url() == "postgresql+psycopg://tangible:secret@db.example.com:5432/tangible"


def test_secret_file_resolution(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    secret = tmp_path / "pw.txt"
    secret.write_text("super-secret\n")
    monkeypatch.setenv("TANGIBLE_DB_PASSWORD_FILE", str(secret))
    monkeypatch.setenv("TANGIBLE_DB_TYPE", "postgresql")
    monkeypatch.setenv("TANGIBLE_DB_HOST", "db")
    monkeypatch.setenv("TANGIBLE_DB_USER", "tangible")
    s = Settings()
    assert s.db_password == "super-secret"


def test_public_url_drives_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TANGIBLE_PUBLIC_URL", "https://tangible.example.com")
    s = Settings()
    assert s.force_https is True
    assert s.session_cookie_secure is True
    assert "tangible.example.com" in s.allowed_hosts


def test_csv_split(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TANGIBLE_CORS_ORIGINS", "https://a.example,https://b.example")
    s = Settings()
    assert s.cors_origins == ["https://a.example", "https://b.example"]
