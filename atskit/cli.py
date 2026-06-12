"""Optional CLI for ATSKit."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import atskit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atskit", description="ATS job discovery toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Stream jobs from all portals in a DB")
    discover.add_argument(
        "--db",
        default=os.environ.get("ATSKIT_DB_PATH"),
        required="ATSKIT_DB_PATH" not in os.environ,
        help="SQLite DB path containing portal_entries (or set ATSKIT_DB_PATH)",
    )
    discover.add_argument("--max-workers", type=int, default=3)
    discover.add_argument("--include-scanned-today", action="store_true")

    list_cmd = sub.add_parser("list", help="List jobs for a single portal slug")
    list_cmd.add_argument("--portal", required=True)
    list_cmd.add_argument("--slug", required=True)

    args = parser.parse_args(argv)

    if args.command == "discover":
        db_path = Path(args.db)
        for result in atskit.discover_jobs(
            db_path,
            skip_scanned_today=not args.include_scanned_today,
            max_workers=args.max_workers,
        ):
            status = "error" if result.error else "ok"
            print(
                f"[{status}] {result.entry.name} ({result.entry.portal}): "
                f"{result.job_count} jobs in {result.duration_ms}ms"
            )
            if result.error:
                print(f"  error: {result.error}")
        return 0

    if args.command == "list":
        jobs = atskit.list_jobs(args.portal, args.slug)
        print(f"{args.portal}/{args.slug}: {len(jobs)} jobs")
        for job in jobs[:20]:
            print(f"  - {job.title} | {job.location}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
