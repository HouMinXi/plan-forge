"""Integration test: scaffold output passes mechanical gates by construction.

Phase 3 contract: check(scaffold_output, llm_clients=[]) must yield zero
BLOCKER and zero HIGH findings from the mechanical layer. This is the
acceptance criterion for T14 -- the skeleton is structurally complete so
the human can focus on content, not on satisfying section requirements.
"""
from __future__ import annotations

from plan_forge.api import check, scaffold
from plan_forge.verdict import Severity


def test_scaffold_output_passes_mechanical_gates(tmp_path) -> None:
    """scaffold() output contains zero BLOCKER or HIGH findings when checked."""
    p = scaffold("contract-check", tmp_path)
    assert p.is_absolute(), f"scaffold() must return an absolute Path; got {p}"
    text = p.read_text(encoding="utf-8")
    v = check(text, llm_clients=[])
    serious = [
        f for f in v.findings
        if f.severity in {Severity.BLOCKER, Severity.HIGH}
    ]
    assert serious == [], [
        (f.check_id, f.severity.name, f.message) for f in serious
    ]


def test_scaffold_output_passes_gates_for_varied_names(tmp_path) -> None:
    """Contract holds for different plan names including hyphens and dots."""
    for name in ("alpha", "my-plan-v2", "plan.2026"):
        sub = tmp_path / name
        sub.mkdir()
        p = scaffold(name, sub)
        text = p.read_text(encoding="utf-8")
        v = check(text, llm_clients=[])
        serious = [
            f for f in v.findings
            if f.severity in {Severity.BLOCKER, Severity.HIGH}
        ]
        assert serious == [], (
            f"name={name!r}: "
            + str([(f.check_id, f.severity.name) for f in serious])
        )
