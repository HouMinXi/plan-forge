"""P6: Metadata currency check.

A frontmatter currency date that contradicts in-body evidence means the plan
misstates its own provenance -- an honesty defect, not a formatting slip.
P6 is HIGH severity because the resolution is a true ownership action: stop
misstating; correct the date or honestly record the update history.

Imprecise dating and verbose update histories are never penalized; only a
body currency-date strictly greater than the MAX of all frontmatter dates
triggers a finding.  A p6-ok marker in the frontmatter suppresses the check.
"""
from __future__ import annotations

import re
from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity


# YYYY-MM-DD date anywhere in text
_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Frontmatter key lines: **Drafted**: / **Status**: / **Updated**: / etc.
_FM_KEY_RE = re.compile(
    r"^\*\*(Drafted|Status|Updated|Revised|Date|Last\s+updated)\*\*\s*:",
    re.IGNORECASE,
)

# Body currency keywords (case-insensitive); a date within 60 chars of one
# of these on the same line is treated as a body currency-date.
_CURRENCY_KW_RE = re.compile(
    r"\b(?:integrated|updated|revised|fixes|as\s+of|current\s+as\s+of|"
    r"completed|merged|shipped|released|last\s+updated)\b",
    re.IGNORECASE,
)

# Escape hatch: suppress all P6 findings for this plan
_P6_OK_RE = re.compile(r"<!--\s*plan-forge:\s*p6-ok")

# H2 heading: marks the end of the frontmatter region
_H2_RE = re.compile(r"^##\s")


def _date_tuple(m: re.Match) -> tuple[int, int, int]:
    """Return (year, month, day) from a _DATE_RE match."""
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def _split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split lines into (frontmatter_lines, body_lines).

    The frontmatter region is everything before the first H2 heading.
    If no H2 is found, the entire document is treated as frontmatter
    (edge case: a plan with no section headings has no body to scan).
    """
    for i, line in enumerate(lines):
        if _H2_RE.match(line):
            return lines[:i], lines[i:]
    return lines, []


def check(parsed: ParsedPlan) -> list[Finding]:
    """Run P6 metadata-currency check on a parsed plan.

    Returns a list of HIGH findings, one per body line whose currency-date
    strictly exceeds the maximum frontmatter currency date.  Returns []
    when the frontmatter carries no exact YYYY-MM-DD, when a p6-ok escape
    hatch is present, or when all body currency-dates are <= fm_latest.
    """
    lines = parsed.raw_text.splitlines()
    fm_lines, body_lines = _split_frontmatter(lines)

    # Check escape hatch first (suppress all P6 for this plan)
    for fm_line in fm_lines:
        if _P6_OK_RE.search(fm_line):
            return []

    fm_dates: list[tuple[tuple[int, int, int], int]] = []  # (date_tuple, 1-based lineno)
    for lineno, fm_line in enumerate(fm_lines, 1):
        if not _FM_KEY_RE.match(fm_line):
            continue
        for m in _DATE_RE.finditer(fm_line):
            fm_dates.append((_date_tuple(m), lineno))

    if not fm_dates:
        # No exact dated frontmatter key -> no check to perform (scaffold case)
        return []

    fm_max_date, fm_max_lineno = max(fm_dates, key=lambda x: x[0])

    findings: list[Finding] = []
    seen: set[tuple[tuple[int, int, int], int]] = set()  # dedup by (date, body_lineno)

    # body_lines[0] is at file line (len(fm_lines) + 1)
    body_offset = len(fm_lines) + 1  # 1-based file line of body_lines[0]

    for idx, body_line in enumerate(body_lines):
        body_lineno = body_offset + idx
        for m in _DATE_RE.finditer(body_line):
            date_tup = _date_tuple(m)
            if date_tup <= fm_max_date:
                continue

            # Check whether a currency keyword appears within 60 chars on the
            # same line.  Measure proximity by character position in the line.
            date_start = m.start()
            date_end = m.end()
            window_start = max(0, date_start - 60)
            window_end = min(len(body_line), date_end + 60)
            window = body_line[window_start:window_end]

            if not _CURRENCY_KW_RE.search(window):
                continue

            # Dedup by (date, body line number)
            key = (date_tup, body_lineno)
            if key in seen:
                continue
            seen.add(key)

            fm_str = "{:04d}-{:02d}-{:02d}".format(*fm_max_date)
            body_str = "{:04d}-{:02d}-{:02d}".format(*date_tup)
            findings.append(Finding(
                check_id="P6.metadata_contradicts_body",
                severity=Severity.HIGH,
                location=f"line:{fm_max_lineno}",
                message=(
                    f"frontmatter currency date {fm_str} contradicts"
                    f" in-body evidence of work on {body_str}"
                    f" (line {body_lineno}); the plan misstates its own"
                    " provenance"
                ),
                fix_hint=(
                    "correct the frontmatter Drafted/Status/Updated date to"
                    " honestly cover work through the latest in-body currency"
                    " date (a date range or an appended update entry is fine"
                    " -- verbose honest dating is not penalized), or add an"
                    " inline <!-- plan-forge: p6-ok (reason) --> marker on"
                    " the frontmatter date line if the in-body date genuinely"
                    " predates drafting"
                ),
            ))

    return findings
