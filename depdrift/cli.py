"""Command line entry point for depdrift."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .lockfile import load
from .review import SEVERITY_ORDER, review, to_markdown


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="depdrift",
        description="Review what changed between two npm lockfiles and what is risky about it.",
    )
    parser.add_argument("old", help="lockfile before the change")
    parser.add_argument("new", nargs="?", help="lockfile after the change (default: current package-lock.json)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--fail-on",
        choices=["none", "low", "medium", "high", "critical"],
        default="none",
        help="exit non-zero when a finding at this severity or worse exists",
    )
    parser.add_argument("--version", action="version", version=f"depdrift {__version__}")
    args = parser.parse_args(argv)

    new_path = args.new or "package-lock.json"
    result = review(load(args.old), load(new_path))

    if args.json:
        print(json.dumps({
            "added": [f"{p.name}@{p.version}" for p in result.added],
            "removed": [f"{p.name}@{p.version}" for p in result.removed],
            "changed": [f"{o.name} {o.version}->{n.version}" for o, n in result.changed],
            "worst": result.worst,
            "findings": [f.as_dict() for f in result.findings],
        }, indent=2))
    else:
        print(to_markdown(result))

    if args.fail_on != "none" and result.findings:
        threshold = SEVERITY_ORDER[args.fail_on]
        if any(SEVERITY_ORDER[f.severity] <= threshold for f in result.findings):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
