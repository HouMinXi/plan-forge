"""Skill runner adapter: analyze and capture subcommands."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

from plan_forge import api
from plan_forge import parser
from plan_forge.arbitration import surface, bundle, capture
from plan_forge.corpus.record import CorpusRecorder


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m plan_forge.adapters.skill.runner",
        description="plan-forge skill runner",
    )
    sub = parser.add_subparsers(dest="subcommand")

    ana = sub.add_parser("analyze", help="Analyze a plan file")
    ana.add_argument("--plan-path", required=True, metavar="PATH")
    ana.add_argument(
        "--arbitration-mode",
        choices=sorted(surface.VALID_MODES),
        default="on_split_evidence_rich",
        metavar="MODE",
    )
    ana.add_argument("--preamble", default=None, metavar="PATH")
    ana.add_argument(
        "--mechanical-only",
        action="store_true",
        default=False,
    )

    cap = sub.add_parser("capture", help="Capture arbitration verdict")
    cap.add_argument("--session-file", required=True, metavar="F")
    cap.add_argument("--index", type=int, required=True, metavar="I")
    cap.add_argument(
        "--verdict",
        choices=["verified", "unverified", "deferred", "abstain"],
        required=True,
        metavar="V",
    )
    cap.add_argument("--rationale", default=None, metavar="R")

    ext = sub.add_parser(
        "extract-citations",
        help="Extract citations from plan External Voices section",
    )
    ext.add_argument("--plan-path", required=True, metavar="PATH")

    return parser


def _cmd_analyze(args: argparse.Namespace) -> int:
    plan_path = args.plan_path
    mode = args.arbitration_mode
    mechanical_only = args.mechanical_only

    preamble: str | None = None
    if args.preamble is not None:
        try:
            with open(args.preamble, encoding="utf-8") as fh:
                preamble = fh.read()
        except OSError as exc:
            print(json.dumps({"error": str(exc)}))
            return 1

    try:
        with open(plan_path, encoding="utf-8") as fh:
            plan_text = fh.read()
    except OSError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    corpus_active = bool(os.environ.get("PLAN_FORGE_CORPUS_URL"))
    llm_clients = [] if mechanical_only else None

    verdict = api.check(
        plan_text,
        plan_path=plan_path,
        arbitration_mode=mode,
        preamble=preamble,
        llm_clients=llm_clients,
    )

    should, to_arb = surface.decide_when_to_arbitrate(
        verdict.findings, mode
    )

    candidates = [
        {
            "index": i,
            "check_id": f.check_id,
            "location": f.location,
            "bundle_text": bundle.build_evidence_bundle(f),
            "finding_id": f.finding_id,
        }
        for i, f in enumerate(to_arb)
    ]

    session_file: str | None = None
    if (
        candidates
        and corpus_active
        and verdict.corpus_run_id is not None
    ):
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(
            {
                "run_id": verdict.corpus_run_id,
                "candidates": candidates,
            },
            tmp,
        )
        tmp.close()
        session_file = tmp.name

    print(
        json.dumps(
            {
                "corpus_active": corpus_active,
                "run_id": verdict.corpus_run_id,
                "engineering": verdict.engineering.value,
                "epistemic": verdict.epistemic.value,
                "summary": verdict.summary(),
                "session_file": session_file,
                "arbitration_candidates": candidates,
            }
        )
    )
    return 0


def _cmd_capture(args: argparse.Namespace) -> int:
    if not os.environ.get("PLAN_FORGE_CORPUS_URL"):
        print(
            json.dumps(
                {"error": "corpus inactive; verdict not persisted"}
            )
        )
        return 1

    try:
        with open(args.session_file, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    try:
        candidates = data["candidates"]
        run_id = data["run_id"]
        n_candidates = len(candidates)
    except (KeyError, TypeError) as exc:
        print(json.dumps({"error": f"malformed session file: {exc}"}))
        return 1

    idx = args.index

    if idx < 0 or idx >= n_candidates:
        print(
            json.dumps({"error": f"index {idx} out of range"})
        )
        return 1

    try:
        bundle_text = candidates[idx]["bundle_text"]
        finding_id = candidates[idx].get("finding_id")
    except (KeyError, TypeError) as exc:
        print(json.dumps({"error": f"malformed session file: {exc}"}))
        return 1
    recorder = CorpusRecorder()
    arb_id = capture.capture_arbitration(
        recorder,
        run_id,
        finding_id=finding_id,
        bundle_text=bundle_text,
        human_verdict=args.verdict,
        human_rationale=args.rationale,
    )
    print(json.dumps({"arbitration_id": arb_id}))
    return 0


def _cmd_extract_citations(args: argparse.Namespace) -> int:
    try:
        with open(args.plan_path, encoding="utf-8") as fh:
            plan_text = fh.read()
    except OSError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1

    parsed = parser.parse(plan_text)
    print(json.dumps(parsed.citations))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the skill runner; returns exit code."""
    argparser = _build_parser()
    args = argparser.parse_args(argv)

    if args.subcommand == "analyze":
        return _cmd_analyze(args)
    if args.subcommand == "capture":
        return _cmd_capture(args)
    if args.subcommand == "extract-citations":
        return _cmd_extract_citations(args)

    argparser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
