"""F2: Duplicate-fact lint.

Tokenizes each section body into capitalized noun-phrase proxies
(bigrams and trigrams).  Phrases appearing in 3+ distinct sections
are flagged as potential single-source-of-truth violations.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Capitalized word / identifier of length >= 3
_CAP_TOKEN_RE = re.compile(r'\b[A-Z][A-Za-z0-9_-]{2,}\b')

# Max findings emitted per plan
_FINDING_CAP = 20


def _extract_ngrams(text: str) -> set[str]:
    """Return set of lowercase bigrams and trigrams of capitalized tokens."""
    tokens = _CAP_TOKEN_RE.findall(text)
    lower = [t.lower() for t in tokens]
    ngrams: set[str] = set()
    for i in range(len(lower)):
        if i + 1 < len(lower):
            ngrams.add(lower[i] + ' ' + lower[i + 1])
        if i + 2 < len(lower):
            ngrams.add(lower[i] + ' ' + lower[i + 1] + ' ' + lower[i + 2])
    return ngrams


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check for duplicate facts appearing in 3+ sections.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        At most 20 F2 findings (sorted by occurrence count desc, then alpha).
    """
    # occurrences: ngram -> set of section headings containing it
    occurrences: dict[str, set[str]] = {}

    for heading, section in parsed.sections.items():
        ngrams = _extract_ngrams(section.body)
        for ng in ngrams:
            occurrences.setdefault(ng, set()).add(heading)

    # Filter to ngrams appearing in >= 3 sections
    flagged = [
        (ng, headings)
        for ng, headings in occurrences.items()
        if len(headings) >= 3
    ]

    # Sort: descending count, then alphabetical for tie-breaking
    flagged.sort(key=lambda x: (-len(x[1]), x[0]))

    heading_words: set[str] = set()
    for heading in parsed.sections:
        heading_words.update(heading.lower().split())

    findings: list[Finding] = []
    for ng, headings in flagged[:_FINDING_CAP]:
        if set(ng.split()) <= heading_words:
            continue
        findings.append(Finding(
            check_id="F2.duplicate_fact",
            severity=Severity.LOW,
            location="line:0",
            message=(
                f"phrase {ng!r} appears in {len(headings)} sections:"
                f" {sorted(headings)!r}"
            ),
            fix_hint=(
                f"declare {ng!r} canonically in one section and"
                f" reference it elsewhere"
            ),
        ))

    return findings
