"""Console script entry point."""

from __future__ import annotations

import argparse
import sys

import uvicorn

from tangible.bootstrap import bootstrap_admin_if_needed, ensure_data_dirs, run_migrations
from tangible.config import get_settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tangible", description="Tangible server CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("serve", help="Run the HTTP server")
    sub.add_parser("migrate", help="Run database migrations")
    sub.add_parser("bootstrap-admin", help="Create initial admin from env if needed")
    sub.add_parser("version", help="Print the installed Tangible version")

    backup = sub.add_parser("backup", help="Write a JSON backup for a user to a file")
    backup.add_argument("username")
    backup.add_argument("output", help="Path to write backup JSON to (use '-' for stdout)")

    restore = sub.add_parser("restore", help="Restore a JSON backup into a user's account")
    restore.add_argument("username")
    restore.add_argument("input", help="Path to backup JSON to read (use '-' for stdin)")

    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    settings = get_settings()
    ensure_data_dirs(settings)

    if args.cmd == "serve":
        if settings.db_auto_migrate:
            run_migrations(settings)
        bootstrap_admin_if_needed(settings)
        uvicorn.run(
            "tangible.main:app",
            host=settings.host,
            port=settings.port,
            proxy_headers=settings.behind_proxy,
            forwarded_allow_ips="*" if settings.behind_proxy else None,
        )
    elif args.cmd == "migrate":
        run_migrations(settings)
    elif args.cmd == "bootstrap-admin":
        bootstrap_admin_if_needed(settings)
    elif args.cmd == "version":
        from tangible import __version__

        print(__version__)
    elif args.cmd == "backup":
        _cmd_backup(settings, args.username, args.output)
    elif args.cmd == "restore":
        _cmd_restore(settings, args.username, args.input)
    return 0


def _cmd_backup(settings, username: str, output: str) -> None:
    import json as _json

    from sqlalchemy import select
    from sqlalchemy.orm import Session as DBSession

    from tangible.db import init_engine
    from tangible.importers import export_user
    from tangible.models import User

    engine = init_engine(settings)
    with DBSession(engine) as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            raise SystemExit(f"User not found: {username}")
        payload = export_user(db, user=user)

    if output == "-":
        _json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        from pathlib import Path

        Path(output).write_text(_json.dumps(payload, indent=2, default=str))


def _cmd_restore(settings, username: str, input_path: str) -> None:
    import json as _json
    from pathlib import Path

    from sqlalchemy import select
    from sqlalchemy.orm import Session as DBSession

    from tangible.db import init_engine
    from tangible.importers import import_backup
    from tangible.models import User

    if input_path == "-":
        payload = _json.load(sys.stdin)
    else:
        payload = _json.loads(Path(input_path).read_text())

    engine = init_engine(settings)
    with DBSession(engine) as db:
        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            raise SystemExit(f"User not found: {username}")
        stats = import_backup(db, user=user, payload=payload)
    print(
        f"Restored: {stats.collections} collections, {stats.items} items, "
        f"{stats.tags} tags, {stats.contacts} contacts, {stats.loans} loans, "
        f"{stats.share_links} share links, {stats.photos} photo records"
    )


if __name__ == "__main__":
    sys.exit(main())
