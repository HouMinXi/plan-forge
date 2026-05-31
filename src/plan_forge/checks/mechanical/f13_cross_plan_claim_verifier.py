"""F13: Cross-plan claim verifier for thin-prose audit references.

In audit/reference/appendix sections, cross-plan references (e.g. "10-02",
"Phase 3", "T07") should be accompanied by at least 10 non-reference words
of prose explaining what the referenced plan contains and why it is relevant.
Entries with fewer than 10 prose words are flagged as MEDIUM findings.
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity
from plan_forge.checks.mechanical.f3_cross_plan_invariant import (
    _PHASE_RE,
    _SUBPLAN_RE,
    _TASK_RE,
    _heading_is_exempt,
    _own_id_set,
)


def _prose_word_count(sentence: str) -> int:
    """Count words in sentence that are not cross-plan reference tokens."""
    count = 0
    for word in sentence.split():
        clean = word.strip(".,;:()")
        if (
            _PHASE_RE.fullmatch(clean)
            or _SUBPLAN_RE.fullmatch(clean)
            or _TASK_RE.fullmatch(clean)
        ):
            continue
        count += 1
    return count


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check that cross-plan refs in audit sections have enough prose context.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        One F13 finding per cross-plan reference with fewer than 10 prose words.
    """
    own = _own_id_set(parsed)
    findings: list[Finding] = []

    for heading, section in parsed.sections.items():
        if not _heading_is_exempt(heading):
            continue
        for pattern in (_PHASE_RE, _SUBPLAN_RE, _TASK_RE):
            for m in pattern.finditer(section.body):
                ref = m.group(0).lower()
                if ref in own:
                    continue
                start = max(0, m.start() - 100)
                end = min(len(section.body), m.end() + 100)
                sentence = section.body[start:end]
                if _prose_word_count(sentence) < 10:
                    body_pos = parsed.raw_text.find(section.body)
                    lineno = (
                        parsed.raw_text[:body_pos].count('\n') + 1
                        if body_pos >= 0
                        else 0
                    )
                    findings.append(Finding(
                        check_id="F13.cross_plan_claim_thin",
                        severity=Severity.MEDIUM,
                        location=f"line:{lineno}",
                        message=(
                            f"cross-plan reference {m.group(0)!r} in"
                            f" audit/references section has fewer than"
                            f" 10 prose words of context"
                        ),
                        fix_hint=(
                            "expand the reference entry to explain what the"
                            " plan contains and why it is relevant"
                        ),
                    ))
    return findings
