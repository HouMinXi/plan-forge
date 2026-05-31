"""F10: Noun-phrase duplicate detection across plan sections.

Flags 3-4 word lowercase phrases that appear in 3 or more distinct sections,
suggesting the same concept is described redundantly rather than declared once
and referenced elsewhere.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "as", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "will", "would", "could", "should", "may",
    "might", "must", "shall", "can", "this", "that", "these",
    "those", "it", "its", "not", "no", "so", "if", "then",
})

_FINDING_CAP = 10


def _extract_noun_phrases(body: str) -> set[str]:
    """Extract 3-4 word noun phrases from a section body, skipping code blocks."""
    in_code = False
    fence_width = ""
    clean_lines: list[str] = []

    for line in body.splitlines():
        stripped = line.strip()
        fence_match = re.match(r'^(`{3,})', stripped)
        if fence_match:
            fence = fence_match.group(1)
            if not in_code:
                in_code = True
                fence_width = fence
            elif fence == fence_width:
                in_code = False
                fence_width = ""
            continue
        if in_code:
            continue
        clean_lines.append(line)

    text = " ".join(clean_lines).lower()
    all_tokens = re.findall(r'\b[a-z][a-z0-9_-]*\b', text)
    tokens = [t for t in all_tokens if t not in _STOPWORDS]

    phrases: set[str] = set()
    for i in range(len(tokens)):
        for width in (3, 4):
            if i + width <= len(tokens):
                phrase = " ".join(tokens[i:i + width])
                if any(len(w) >= 4 for w in phrase.split()):
                    phrases.add(phrase)
    return phrases


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check for noun phrases repeated across 3 or more distinct sections.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        At most 10 F10 findings (sorted by occurrence count desc, then alpha).
    """
    occurrences: dict[str, set[str]] = {}

    for heading, section in parsed.sections.items():
        for phrase in _extract_noun_phrases(section.body):
            occurrences.setdefault(phrase, set()).add(heading)

    flagged = [
        (phrase, headings)
        for phrase, headings in occurrences.items()
        if len(headings) >= 3
    ]
    flagged.sort(key=lambda x: (-len(x[1]), x[0]))

    findings: list[Finding] = []
    for phrase, headings in flagged[:_FINDING_CAP]:
        findings.append(Finding(
            check_id="F10.noun_phrase_duplicate",
            severity=Severity.LOW,
            location="line:0",
            message=(
                f"phrase {phrase!r} appears in {len(headings)} sections:"
                f" {sorted(headings)!r}"
            ),
            fix_hint=(
                f"declare {phrase!r} once canonically and reference it elsewhere"
            ),
        ))
    return findings
