"""End-to-end test of the `tangible` CLI (backup/restore round trip)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tangible.auth.service import create_user
from tangible.bootstrap import run_migrations
from tangible.db import init_engine


@pytest.fixture()
def cli_env(monkeypatch: pytest.MonkeyPatch, settings):
    """Ensure subprocess sees the same data dir as the in-process tests."""
    monkeypatch.setenv("TANGIBLE_DATA_DIR", str(settings.data_dir))
    monkeypatch.setenv("TANGIBLE_CONFIG_DIR", str(settings.config_dir))
    monkeypatch.setenv("TANGIBLE_DB_TYPE", "sqlite")
    monkeypatch.setenv("TANGIBLE_DB_AUTO_MIGRATE", "false")
    monkeypatch.setenv("TANGIBLE_PUBLIC_URL", "http://testserver")
    run_migrations(settings)
    # Create the test user directly — we don't go through /auth/register
    # because that would require a running server.
    from sqlalchemy.orm import Session as DBSession

    engine = init_engine(settings)
    with DBSession(engine) as db:
        create_user(
            db,
            username="alice",
            password="correct horse battery staple",
            email="alice@example.com",
            is_admin=True,
        )
        db.commit()
    return settings


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "tangible.cli", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_version(cli_env) -> None:
    r = _run("version")
    assert r.returncode == 0, r.stderr
    from tangible import __version__

    assert r.stdout.strip() == __version__


def test_cli_backup_restore_roundtrip(cli_env, tmp_path: Path) -> None:
    out = tmp_path / "backup.json"
    r = _run("backup", "alice", str(out))
    assert r.returncode == 0, r.stderr
    payload = json.loads(out.read_text())
    assert payload["version"] == 1
    assert "collections" in payload
    assert "items" in payload

    r2 = _run("restore", "alice", str(out))
    assert r2.returncode == 0, r2.stderr
    assert "Restored:" in r2.stdout


def test_cli_backup_unknown_user_exits_nonzero(cli_env, tmp_path: Path) -> None:
    r = _run("backup", "ghost", str(tmp_path / "out.json"))
    assert r.returncode != 0
    assert "User not found" in (r.stderr + r.stdout)
