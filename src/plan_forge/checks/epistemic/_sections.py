"""Shared section-finder helper for epistemic gates.

All section-based gates (G1, G3, G5, G7) locate their required section
by heading keyword using this helper. Centralising here avoids inlining
the same loop in each gate module.
"""
from __future__ import annotations

from plan_forge.parser import ParsedPlan, ParsedSection


def find_section(parsed: ParsedPlan, *keywords: str) -> ParsedSection | None:
    """Return the first section whose heading contains ALL keywords.

    The match is case-insensitive. Returns None when no section matches.
    """
    for section in parsed.sections.values():
        h = section.heading.lower()
        if all(kw.lower() in h for kw in keywords):
            return section
    return None
