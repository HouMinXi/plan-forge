"""Retroactive audit runner: discovers archived forge Phase 2 sub-plans.

Discovery only -- enumerating the plan paths so a caller can iterate over them.
Running plan_forge.check and computing coverage are not implemented here.
"""
from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path

DEFAULT_PATTERN = "02-0*-PLAN.md"


def discover_plans(base_dir, pattern: str = DEFAULT_PATTERN) -> list[Path]:
    """Return sorted archived plan paths under base_dir matching pattern.

    base_dir example:
    ~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite

    Returns [] if base_dir is not an existing directory.
    """
    base = Path(base_dir).expanduser()
    if not base.is_dir():
        return []
    matches = [p for p in base.iterdir() if fnmatch.fnmatch(p.name, pattern)]
    return sorted(matches)


def main(argv=None) -> int:
    """Enumerate archived forge Phase 2 sub-plans."""
    parser = argparse.ArgumentParser(
        description="Enumerate archived forge Phase 2 sub-plans (discovery only)."
    )
    parser.add_argument(
        "base_dir",
        help=(
            "Directory containing archived plan files, e.g. "
            "~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite"
        ),
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=f"Glob pattern for plan filenames (default: {DEFAULT_PATTERN!r})",
    )
    args = parser.parse_args(argv)

    plans = discover_plans(args.base_dir, args.pattern)

    if not plans:
        print(f"no plans found in {args.base_dir!r} matching {args.pattern!r}")
        return 1

    for plan in plans:
        print(plan)

    print(f"\nFound {len(plans)} plan(s). Running checks is not implemented in this runner.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
