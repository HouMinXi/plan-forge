"""CLI entry point for plan-forge.

Provides five subcommands (check, scaffold, audit-retroactive,
record-outcome, abandonment-check) that wrap api.check(), api.scaffold(),
and the corpus tools for shell and CI usage.

Exit-code contract (CI-facing):
  0 = PASS / scaffold written / outcome recorded / tombstone absent
  1 = engineering or epistemic FAIL / outcome type invalid
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
    verdict = api.check(
        plan_text,
        plan_path=str(plan_path),
        llm_clients=llm_clients,
        preamble=preamble,
        corpus_private=args.corpus_private,
    )
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
                plan_text,
                plan_path=str(filepath),
                llm_clients=llm_clients,
                corpus_private=args.corpus_private,
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


def _tools_dir() -> str:
    """Return the absolute path to the repo-root tools/ directory.

    main.py lives at src/plan_forge/adapters/cli/main.py; going four
    parents up reaches the repo root, and tools/ is a sibling of src/.
    """
    return str(Path(__file__).resolve().parents[4] / "tools")


def _ensure_tools_on_path() -> None:
    """Add the repo-root tools/ directory to sys.path if absent.

    tools/ is not installed as a package (it is not under src/).  Tests
    and the CLI both need this one-time path injection to import from it.
    """
    tools = _tools_dir()
    if tools not in sys.path:
        sys.path.insert(0, tools)


def _cmd_record_outcome(args: argparse.Namespace) -> int:
    """Handle the 'record-outcome' subcommand."""
    _ensure_tools_on_path()
    import outcomes_cli  # noqa: PLC0415
    return outcomes_cli.record(args)


def _cmd_abandonment_check(args: argparse.Namespace) -> int:
    """Handle the 'abandonment-check' subcommand."""
    _ensure_tools_on_path()
    import abandon  # noqa: PLC0415

    db_path = Path(args.db_path)
    result = abandon.check_abandonment(db_path, args.version)
    if result is not None:
        print(f"ABANDONMENT.md written: {result}")
        return 1
    print("no abandonment triggered")
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
        help="Check a plan document against G1-G10 and F1-F9 gates.",
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
    check_p.add_argument(
        "--corpus-private",
        action="store_true",
        default=False,
        help="Omit plan text from corpus record; store hash only.",
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
    audit_p.add_argument(
        "dir", help="Directory containing plan markdown files."
    )
    audit_p.add_argument(
        "--mechanical-only",
        action="store_true",
        default=False,
        help="Skip LLM-based checks; run mechanical gates only.",
    )
    audit_p.add_argument(
        "--corpus-private",
        action="store_true",
        default=False,
        help="Omit plan text from corpus records; store hash only.",
    )

    # record-outcome
    ro_p = subparsers.add_parser(
        "record-outcome",
        help="Record a predicted-vs-actual outcome into the corpus.",
    )
    ro_p.add_argument(
        "run_id",
        type=int,
        help="The plan_run ID the outcome is linked to.",
    )
    ro_p.add_argument(
        "--type",
        required=True,
        metavar="OUTCOME_TYPE",
        help=(
            "Outcome type: predicted_manifested, "
            "predicted_did_not_manifest, "
            "unpredicted_occurred, plan_succeeded."
        ),
    )
    ro_p.add_argument(
        "--recorder",
        required=True,
        help="Name or identifier of the person recording the outcome.",
    )
    ro_p.add_argument(
        "--evidence",
        default=None,
        help="Post-hoc evidence text (optional).",
    )
    ro_p.add_argument(
        "--date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Outcome date (default: today UTC).",
    )
    ro_p.add_argument(
        "--finding-id",
        type=int,
        default=None,
        dest="finding_id",
        help="The finding_id this outcome is linked to (optional).",
    )
    ro_p.add_argument(
        "--notes",
        default=None,
        help="Free-text notes (optional).",
    )

    # abandonment-check
    ab_p = subparsers.add_parser(
        "abandonment-check",
        help=(
            "Generate ABANDONMENT.md if 6+ months elapsed with 0"
            " outcomes recorded."
        ),
    )
    ab_p.add_argument(
        "db_path",
        help="Path to the corpus SQLite DB file.",
    )
    ab_p.add_argument(
        "--version",
        required=True,
        help="Current plan-forge version string (e.g. 0.1.0).",
    )

    return parser


_HANDLERS = {
    "check": _cmd_check,
    "scaffold": _cmd_scaffold,
    "audit-retroactive": _cmd_audit,
    "record-outcome": _cmd_record_outcome,
    "abandonment-check": _cmd_abandonment_check,
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
