"""CLI entry point for plan-forge.

Provides three subcommands (check, scaffold, audit-retroactive) that
wrap api.check() and api.scaffold() for shell and CI usage.

Exit-code contract (CI-facing):
  0 = PASS / scaffold written
  1 = engineering or epistemic FAIL
  2 = reserved by argparse for usage errors
  3 = epistemic VISION (structurally a vision, not a defect)
  4 = runtime/IO error (missing file, unreadable, unexpected exception)
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

from plan_forge import api
from plan_forge.verdict import EngineeringVerdict, EpistemicVerdict


def _verdict_to_exit_code(v: api.Verdict) -> int:
    """Map a Verdict to the CLI exit-code contract.

    FAIL (engineering or epistemic) takes precedence over VISION.
    """
    if (v.engineering == EngineeringVerdict.FAIL
            or v.epistemic == EpistemicVerdict.FAIL):
        return 1
    if v.epistemic == EpistemicVerdict.VISION:
        return 3
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Handle the 'check' subcommand."""
    plan_path = Path(args.plan)
    try:
        plan_text = plan_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4

    preamble = None
    if args.preamble is not None:
        preamble_path = Path(args.preamble)
        try:
            preamble = preamble_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 4

    llm_clients = [] if args.mechanical_only else None
    verdict = api.check(plan_text, llm_clients=llm_clients, preamble=preamble)
    print(verdict.summary())
    return _verdict_to_exit_code(verdict)


def _cmd_scaffold(args: argparse.Namespace) -> int:
    """Handle the 'scaffold' subcommand."""
    output_dir = Path(args.output_dir) if args.output_dir else None
    try:
        path = api.scaffold(args.name, output_dir=output_dir)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    print(path)
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    """Handle the 'audit-retroactive' subcommand."""
    audit_dir = Path(args.dir)
    if not audit_dir.is_dir():
        print(f"error: not a directory: {audit_dir}", file=sys.stderr)
        return 4

    # SUBSPEC interpretation: glob *.md is case-sensitive lowercase per
    # POSIX glob; .MD/.mD are NOT matched.
    md_files = sorted(glob.glob("*.md", root_dir=str(audit_dir)))
    if not md_files:
        print("no plans found")
        return 0

    # Keys: all valid per-file rollup codes (0/1/3/4). Code 2 is argparse-
    # reserved and propagates as SystemExit before any handler runs; it
    # cannot appear inside this loop, so no key 2 is needed.
    counts = {0: 0, 1: 0, 3: 0, 4: 0}
    llm_clients = [] if args.mechanical_only else None

    for filename in md_files:
        filepath = audit_dir / filename
        try:
            plan_text = filepath.read_text(encoding="utf-8")
            # preamble is intentionally omitted: a batch audit applies no
            # single orchestrator preamble across heterogeneous plans.
            verdict = api.check(
                plan_text, llm_clients=llm_clients,
            )
            code = _verdict_to_exit_code(verdict)
            print(
                f"{filename}: engineering={verdict.engineering.value}"
                f" epistemic={verdict.epistemic.value}"
            )
        except Exception as exc:
            code = 4
            # SUBSPEC interpretation: per-file ERROR lines go to stdout (not
            # stderr) so the batch output is a stable N-line block for CI
            # parsers.  Only CLI-level errors (dir missing) go to stderr.
            print(f"{filename}: ERROR {exc}")
        counts[code] += 1

    total = sum(counts.values())
    print(
        f"{total} plans: {counts[0]} pass, {counts[1]} fail,"
        f" {counts[3]} vision, {counts[4]} error"
    )

    # Worst-code rollup: 4 > 1 > 3 > 0
    if counts[4]:
        return 4
    if counts[1]:
        return 1
    if counts[3]:
        return 3
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="plan-forge",
        description="Epistemological gate enforcer for plan documents.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    check_p = subparsers.add_parser(
        "check",
        help="Check a plan document against G1-G10 and F1-F7 gates.",
    )
    check_p.add_argument("plan", help="Path to the plan markdown file.")
    check_p.add_argument(
        "--mechanical-only",
        action="store_true",
        default=False,
        help="Skip LLM-based checks; run mechanical gates only.",
    )
    check_p.add_argument(
        "--preamble",
        default=None,
        metavar="FILE",
        help="Path to an orchestrator preamble file for F6 check.",
    )

    # scaffold
    scaffold_p = subparsers.add_parser(
        "scaffold",
        help="Generate a plan skeleton from the bundled template.",
    )
    scaffold_p.add_argument("name", help="Base name for the plan file (slug).")
    scaffold_p.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Directory to write the scaffold into (default: cwd).",
    )

    # audit-retroactive
    audit_p = subparsers.add_parser(
        "audit-retroactive",
        help="Batch-audit all *.md files in a directory.",
    )
    audit_p.add_argument("dir", help="Directory containing plan markdown files.")
    audit_p.add_argument(
        "--mechanical-only",
        action="store_true",
        default=False,
        help="Skip LLM-based checks; run mechanical gates only.",
    )

    return parser


_HANDLERS = {
    "check": _cmd_check,
    "scaffold": _cmd_scaffold,
    "audit-retroactive": _cmd_audit,
}


def main(argv: list[str] | None = None) -> int:
    """CLI dispatcher. Returns an exit code (0-4).

    argparse --help and usage errors raise SystemExit (0 or 2) before
    any handler runs; those propagate to the caller (setuptools
    console_scripts wraps main() with sys.exit()).

    Any unexpected exception from a handler is caught and yields exit 4
    with a message on stderr, so no traceback escapes.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _HANDLERS[args.command]
    try:
        return handler(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
