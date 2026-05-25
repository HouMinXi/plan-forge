#!/usr/bin/env python3
"""
Host-search injection eval runner.

Tests whether deepseek/mimo can accurately judge citation resolvability
when given the host's exhaustive search evidence, vs host judgment.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plan_forge.llm.client import parse_verdict_response
from plan_forge.llm.deepseek_client import DeepSeekClient
from plan_forge.llm.mimo_client import MimoClient
from plan_forge.llm.prompts import load as load_prompt
from plan_forge.checks.epistemic._evidence import (
    G8_RESOLVED_VIA_SEARCH,
    G8_RESOLVED_BY_KNOWLEDGE,
    G8_UNCERTAIN,
    G8_UNRESOLVABLE,
    verdict_matches,
)


@dataclass
class VerdictResult:
    """Result for one condition on one citation."""

    citation_id: str
    condition: str
    raw_verdict: str | None
    normalized_verdict: str | None
    grade: str | None
    error: str | None
    fabricated_resolution: bool


def get_api_key(provider: str) -> str:
    """Get API key from env or pass."""
    env_var = f"PLAN_FORGE_{provider.upper()}_API_KEY"
    key = os.environ.get(env_var)
    if key:
        return key

    import subprocess

    try:
        result = subprocess.run(
            ["pass", "show", f"api/{provider.lower()}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n")[0]
    except Exception as e:
        raise RuntimeError(f"Cannot get {provider} key: {e}") from e


def build_prompt(
    citation: str, evidence_bundle: list[dict[str, Any]], with_evidence: bool
) -> str:
    """Build G8 prompt with optional evidence injection."""
    base = load_prompt("g8_citation_resolvability_v0")
    input_block = "\n\nINPUT:\n" + json.dumps(
        {"citation_text": citation, "context": "External Voices"}
    )

    if not with_evidence:
        return base + input_block

    evidence_lines = []
    if not evidence_bundle:
        evidence_lines.append("No results found after exhaustive search.\n")
    else:
        for i, hit in enumerate(evidence_bundle, 1):
            tier = hit.get("tier", "UNKNOWN")
            domain = hit.get("domain", "unknown")
            title = hit.get("title", "")
            snippet = hit.get("snippet", "")
            evidence_lines.append(
                f"[{i}] (tier={tier}, {domain}) {title} -- {snippet}\n"
            )

    evidence_block = (
        "\n\nHOST-PROVIDED SEARCH EVIDENCE (raw hits, host-tiered; "
        "treat as the\nresult of an exhaustive web search performed "
        "on your behalf):\n" + "".join(evidence_lines)
    )

    tool_suppression = (
        "\n\nBase your verdict SOLELY on the provided evidence above. "
        "Do NOT attempt to search or call any tool."
    )

    return base + input_block + evidence_block + tool_suppression


def normalize_verdict(raw: str | None) -> str | None:
    """Normalize to RESOLVED/UNCERTAIN/UNRESOLVABLE."""
    if raw is None:
        return None
    if verdict_matches(raw, G8_RESOLVED_VIA_SEARCH) or verdict_matches(
        raw, G8_RESOLVED_BY_KNOWLEDGE
    ):
        return "RESOLVED"
    if verdict_matches(raw, G8_UNCERTAIN):
        return "UNCERTAIN"
    if verdict_matches(raw, G8_UNRESOLVABLE):
        return "UNRESOLVABLE"
    return None


def grade_verdict(
    normalized: str | None, gt: str, category: str, raw: str | None
) -> tuple[str | None, bool]:
    """
    Grade verdict vs GT.

    Returns (grade, fabricated_resolution).
    """
    if normalized is None:
        return (None, False)

    fabricated = False
    if category == "not_found" and raw and verdict_matches(
        raw, G8_RESOLVED_VIA_SEARCH
    ):
        fabricated = True

    if gt == "RESOLVED":
        if normalized == "RESOLVED":
            return ("CORRECT", fabricated)
        if normalized == "UNCERTAIN":
            return ("CONSERVATIVE", fabricated)
        if normalized == "UNRESOLVABLE":
            return ("DANGEROUS", fabricated)
    elif gt == "UNRESOLVABLE":
        if normalized == "UNRESOLVABLE":
            return ("CORRECT", fabricated)
        if normalized == "UNCERTAIN":
            return ("CONSERVATIVE", fabricated)
        if normalized == "RESOLVED":
            return ("DANGEROUS", fabricated)

    return (None, fabricated)


def call_model(
    client: DeepSeekClient | MimoClient,
    prompt: str,
    citation_id: str,
    condition: str,
) -> tuple[str | None, str | None]:
    """
    Call model and return (raw_verdict, error).

    Returns (verdict, None) on success, (None, error_msg) on failure.
    """
    try:
        cache_key = {
            "eval": "hostsearch",
            "id": citation_id,
            "cond": condition,
            "prompt_version": "g8_citation_resolvability_v0",
        }
        resp = client.call(
            prompt, tool_use_schema=None, cache_key_inputs=cache_key
        )

        if resp.verdict:
            return (resp.verdict, None)

        if resp.reasoning:
            parsed = parse_verdict_response(resp.reasoning)
            if parsed and parsed[0]:
                return (parsed[0], None)

        return (None, f"No verdict (reasoning={bool(resp.reasoning)})")
    except Exception as e:
        return (None, str(e))


def run_condition(
    client: DeepSeekClient | MimoClient | None,
    fixtures: list[dict[str, Any]],
    condition: str,
    with_evidence: bool,
) -> list[VerdictResult]:
    """Run one condition across all fixtures."""
    results = []

    for fixture in fixtures:
        cid = fixture["id"]
        category = fixture["category"]
        citation = fixture["citation"]
        gt = fixture["gt_verdict"]
        evidence = fixture.get("evidence_bundle", [])

        if condition == "host":
            raw = fixture["host_verdict"]
            normalized = normalize_verdict(raw)
            grade, fabricated = grade_verdict(normalized, gt, category, raw)
            results.append(
                VerdictResult(
                    citation_id=cid,
                    condition=condition,
                    raw_verdict=raw,
                    normalized_verdict=normalized,
                    grade=grade,
                    error=None,
                    fabricated_resolution=fabricated,
                )
            )
            continue

        prompt = build_prompt(citation, evidence, with_evidence)
        raw, error = call_model(client, prompt, cid, condition)
        normalized = normalize_verdict(raw)
        grade, fabricated = grade_verdict(normalized, gt, category, raw)

        results.append(
            VerdictResult(
                citation_id=cid,
                condition=condition,
                raw_verdict=raw,
                normalized_verdict=normalized,
                grade=grade,
                error=error,
                fabricated_resolution=fabricated,
            )
        )

    return results


def compute_summary(
    results: list[VerdictResult], fixtures: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute summary stats per category."""
    summary = {}

    for category in ["resolvable", "not_found", "contradiction"]:
        cat_fixtures = [f["id"] for f in fixtures if f["category"] == category]
        cat_results = [r for r in results if r.citation_id in cat_fixtures]

        correct = sum(1 for r in cat_results if r.grade == "CORRECT")
        conservative = sum(1 for r in cat_results if r.grade == "CONSERVATIVE")
        dangerous = sum(1 for r in cat_results if r.grade == "DANGEROUS")
        unparseable = sum(
            1 for r in cat_results if r.grade is None and r.error is None
        )
        fabricated = sum(1 for r in cat_results if r.fabricated_resolution)
        errors = sum(1 for r in cat_results if r.error)
        total = len(cat_results)

        summary[category] = {
            "total": total,
            "correct": correct,
            "conservative": conservative,
            "dangerous": dangerous,
            "unparseable": unparseable,
            "fabricated": fabricated,
            "errors": errors,
        }

    overall = {
        "total": sum(s["total"] for s in summary.values()),
        "correct": sum(s["correct"] for s in summary.values()),
        "conservative": sum(s["conservative"] for s in summary.values()),
        "dangerous": sum(s["dangerous"] for s in summary.values()),
        "unparseable": sum(s["unparseable"] for s in summary.values()),
        "fabricated": sum(s["fabricated"] for s in summary.values()),
        "errors": sum(s["errors"] for s in summary.values()),
    }
    summary["overall"] = overall

    return summary


def format_detail_table(
    fixtures: list[dict[str, Any]], all_results: dict[str, list[VerdictResult]]
) -> str:
    """Format detail table: row per citation, column per condition."""
    lines = []
    lines.append("# Detail Table\n")

    conditions = [
        "ds_evidence",
        "ds_noevidence",
        "mimo_thinkon_evidence",
        "mimo_thinkon_noevidence",
        "mimo_thinkoff_evidence",
        "mimo_thinkoff_noevidence",
        "host",
    ]

    cond_abbr = {
        "ds_evidence": "ds_evi",
        "ds_noevidence": "ds_no",
        "mimo_thinkon_evidence": "mo_on_e",
        "mimo_thinkon_noevidence": "mo_on_n",
        "mimo_thinkoff_evidence": "mo_off_e",
        "mimo_thinkoff_noevidence": "mo_off_n",
        "host": "host",
    }

    header_cols = ["ID", "Citation", "GT"] + [cond_abbr[c] for c in conditions]
    lines.append("| " + " | ".join(header_cols) + " |")
    lines.append("|" + "|".join(["-" * 4] * len(header_cols)) + "|")

    for fixture in fixtures:
        cid = fixture["id"]
        citation_short = fixture["citation"][:40] + "..."
        gt = fixture["gt_verdict"][:4]

        row = [cid, citation_short, gt]

        for cond in conditions:
            results = all_results.get(cond, [])
            match = next((r for r in results if r.citation_id == cid), None)
            if not match:
                row.append("?")
            elif match.error:
                row.append("ERR")
            else:
                norm = (match.normalized_verdict or "?")[:4]
                grade = (match.grade or "?")[0]
                row.append(f"{norm}/{grade}")

        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def format_summary_table(
    condition: str, summary: dict[str, Any]
) -> list[str]:
    """Format summary stats for one condition."""
    lines = []
    lines.append(f"\n## {condition}\n")
    lines.append(
        "| Category | Total | Correct | Conservative | Dangerous | "
        "Unparseable | Fabricated | Errors |"
    )
    lines.append("|----|----|----|----|----|----|----|---|")

    for cat in ["resolvable", "not_found", "contradiction", "overall"]:
        s = summary[cat]
        lines.append(
            f"| {cat:13} | {s['total']:5} | {s['correct']:7} | "
            f"{s['conservative']:12} | {s['dangerous']:9} | "
            f"{s['unparseable']:11} | {s['fabricated']:10} | "
            f"{s['errors']:6} |"
        )

    return lines


def generate_report(
    fixtures: list[dict[str, Any]],
    all_results: dict[str, list[VerdictResult]],
) -> tuple[str, dict[str, Any]]:
    """Generate markdown and JSON reports."""
    md_lines = []
    md_lines.append("# Host-Search Injection Eval Report\n")

    md_lines.append(format_detail_table(fixtures, all_results))

    summaries = {}
    for cond, results in all_results.items():
        summary = compute_summary(results, fixtures)
        summaries[cond] = summary
        md_lines.extend(format_summary_table(cond, summary))

    md_lines.append("\n## Headline Comparisons\n")

    def pct(num, denom):
        return f"{100 * num / denom:.1f}%" if denom > 0 else "N/A"

    ds_evi = summaries.get("ds_evidence", {}).get("overall", {})
    ds_no = summaries.get("ds_noevidence", {}).get("overall", {})
    mimo_on_evi = summaries.get("mimo_thinkon_evidence", {}).get("overall", {})
    mimo_on_no = summaries.get("mimo_thinkon_noevidence", {}).get("overall", {})
    mimo_off_evi = summaries.get("mimo_thinkoff_evidence", {}).get("overall", {})
    mimo_off_no = summaries.get("mimo_thinkoff_noevidence", {}).get("overall", {})
    host_sum = summaries.get("host", {}).get("overall", {})

    md_lines.append("### Evidence vs No-evidence\n")
    ds_evi_pct = pct(ds_evi.get("correct", 0), ds_evi.get("total", 0))
    ds_no_pct = pct(ds_no.get("correct", 0), ds_no.get("total", 0))
    mimo_on_evi_pct = pct(mimo_on_evi.get("correct", 0), mimo_on_evi.get("total", 0))
    mimo_on_no_pct = pct(mimo_on_no.get("correct", 0), mimo_on_no.get("total", 0))
    mimo_off_evi_pct = pct(mimo_off_evi.get("correct", 0), mimo_off_evi.get("total", 0))
    mimo_off_no_pct = pct(mimo_off_no.get("correct", 0), mimo_off_no.get("total", 0))
    md_lines.append(
        f"- ds_evidence: {ds_evi_pct} vs ds_noevidence: {ds_no_pct}"
    )
    md_lines.append(
        f"- mimo_thinkon_evidence: {mimo_on_evi_pct} "
        f"vs mimo_thinkon_noevidence: {mimo_on_no_pct}"
    )
    md_lines.append(
        f"- mimo_thinkoff_evidence: {mimo_off_evi_pct} "
        f"vs mimo_thinkoff_noevidence: {mimo_off_no_pct}"
    )

    md_lines.append("\n### Weak-with-evidence vs Host\n")
    host_pct = pct(host_sum.get("correct", 0), host_sum.get("total", 0))
    md_lines.append(f"- ds_evidence: {ds_evi_pct}")
    md_lines.append(f"- mimo_thinkon_evidence: {mimo_on_evi_pct}")
    md_lines.append(f"- mimo_thinkoff_evidence: {mimo_off_evi_pct}")
    md_lines.append(f"- host: {host_pct}")

    md_lines.append("\n### Mimo thinking-on vs thinking-off\n")
    md_lines.append(
        f"- with evidence: thinkon {mimo_on_evi_pct} vs thinkoff {mimo_off_evi_pct}"
    )
    md_lines.append(
        f"- without evidence: thinkon {mimo_on_no_pct} vs thinkoff {mimo_off_no_pct}"
    )

    md_lines.append("\n### Not-found Honesty\n")
    for cond in [
        "ds_evidence",
        "mimo_thinkon_evidence",
        "mimo_thinkoff_evidence",
        "host",
    ]:
        s = summaries.get(cond, {}).get("not_found", {})
        md_lines.append(
            f"- {cond}: dangerous={s.get('dangerous', 0)}, "
            f"fabricated={s.get('fabricated', 0)}"
        )

    md_report = "\n".join(md_lines)

    json_report = {
        "fixtures_count": len(fixtures),
        "conditions": list(all_results.keys()),
        "summaries": summaries,
        "details": [
            {
                "citation_id": r.citation_id,
                "condition": r.condition,
                "raw_verdict": r.raw_verdict,
                "normalized_verdict": r.normalized_verdict,
                "grade": r.grade,
                "error": r.error,
                "fabricated_resolution": r.fabricated_resolution,
            }
            for results in all_results.values()
            for r in results
        ],
    }

    return (md_report, json_report)


def find_repo_root(start: Path) -> Path:
    """Walk up from start until pyproject.toml is found."""
    current = start.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise FileNotFoundError(
        "Could not locate repo root (no pyproject.toml found)"
    )


def main():
    """Run the eval."""
    eval_dir = Path(__file__).parent
    repo_root = find_repo_root(eval_dir)
    fixtures_path = (
        repo_root / "tests" / "fixtures" / "g8_hostsearch_fixtures.json"
    )

    with open(fixtures_path, encoding="utf-8") as f:
        fixtures = json.load(f)

    print(f"Loaded {len(fixtures)} fixtures from {fixtures_path}")

    deepseek_key = get_api_key("deepseek")
    mimo_key = get_api_key("mimo")

    ds_client = DeepSeekClient(api_key=deepseek_key)
    mimo_thinkon = MimoClient(api_key=mimo_key)
    mimo_thinkoff = MimoClient(api_key=mimo_key, disable_thinking=True)

    all_results = {}

    print("\nRunning ds_evidence...")
    all_results["ds_evidence"] = run_condition(
        ds_client, fixtures, "ds_evidence", with_evidence=True
    )

    print("Running ds_noevidence...")
    all_results["ds_noevidence"] = run_condition(
        ds_client, fixtures, "ds_noevidence", with_evidence=False
    )

    print("Running mimo_thinkon_evidence...")
    all_results["mimo_thinkon_evidence"] = run_condition(
        mimo_thinkon, fixtures, "mimo_thinkon_evidence", with_evidence=True
    )

    print("Running mimo_thinkon_noevidence...")
    all_results["mimo_thinkon_noevidence"] = run_condition(
        mimo_thinkon, fixtures, "mimo_thinkon_noevidence", with_evidence=False
    )

    print("Running mimo_thinkoff_evidence...")
    all_results["mimo_thinkoff_evidence"] = run_condition(
        mimo_thinkoff, fixtures, "mimo_thinkoff_evidence", with_evidence=True
    )

    print("Running mimo_thinkoff_noevidence...")
    all_results["mimo_thinkoff_noevidence"] = run_condition(
        mimo_thinkoff, fixtures, "mimo_thinkoff_noevidence", with_evidence=False
    )

    print("Running host...")
    all_results["host"] = run_condition(
        None, fixtures, "host", with_evidence=False
    )

    md_report, json_report = generate_report(fixtures, all_results)

    print("\n" + md_report)

    report_md_path = eval_dir / "report.md"
    report_json_path = eval_dir / "report.json"

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(md_report)

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2)

    print(f"\nReports written to {report_md_path} and {report_json_path}")


if __name__ == "__main__":
    main()
