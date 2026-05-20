"""Markdown plan parser -- produces ParsedPlan.

Uses line-by-line string processing (no external tokenizer needed for
the structured sections in plan documents).  Includes:

  - Section extraction (## and ### headings)
  - SC table parsing (rows matching SC-N / SC-Na patterns)
  - Risk register parsing (Known / Gray Rhinos / Black Swans subsections)
  - Hedge word detection with fence-width-aware in_code_block state machine
  - Citation extraction from External Voices section
  - G9 anchor extraction + quantitative claims without anchor
  - ai_smell_phrases: not populated in v0.1; reserved for future extension
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Supporting dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ParsedSection:
    heading: str
    level: int
    body: str
    line_start: int
    line_end: int


@dataclass
class ParsedSC:
    """Success Criterion entry from SC table.

    number is the numeric portion (e.g. 2 for SC-2a).
    suffix captures the alphabetic variant (e.g. "a" for SC-2a, "" for SC-1).
    full_id is the raw string from the table cell (e.g. "SC-2a").
    """
    number: int
    suffix: str
    full_id: str
    name: str
    body: str
    fail_condition: str | None
    line: int


@dataclass
class ParsedRisk:
    bucket: str           # "known" / "gray_rhino" / "black_swan"
    description: str
    denial_reason: str | None
    survival_plan: str | None


@dataclass
class ParsedAnchor:
    """G9: per-claim anchor citation extracted from plan text."""
    claim_text: str    # the quantitative claim text
    anchor_text: str   # the cited anchor content
    anchor_type: str   # "url" / "project_name" / "prototype" / "publication"
                       # / "in_plan_derivation"
    line: int


@dataclass
class ParsedPlan:
    raw_text: str
    sections: dict[str, ParsedSection] = field(default_factory=dict)
    sc_table: list[ParsedSC] = field(default_factory=list)
    risks: list[ParsedRisk] = field(default_factory=list)
    hedge_word_locations: list[tuple[int, str]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    # not populated in v0.1; reserved for future anti-AI phrase detection
    ai_smell_phrases: list[tuple[int, str]] = field(default_factory=list)
    anchors: list[ParsedAnchor] = field(default_factory=list)
    quantitative_claims_without_anchor: list[tuple[int, str]] = field(
        default_factory=list
    )


# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

# G4 hedge words (11-word canonical list).
# PLAN spec: "maybe / likely / probably / perhaps / possibly / seems /
#  appears / should / could / might / may"
# Code regex MUST match this list exactly (P5 interface-symmetry rule).
_HEDGE_RE = re.compile(
    r'\b(maybe|likely|probably|perhaps|possibly|seems|appears|'
    r'should|could|might|may)\b',
    re.IGNORECASE,
)

# SC row: first cell matches SC-N or SC-Na (e.g., SC-1, SC-2a, SC-2b)
_SC_ROW_RE = re.compile(r'^SC-(\d+)([a-z]?)$', re.IGNORECASE)

# Citation pattern for External Voices: Author(s) + year + title start.
# Permissive: capture more than reject.
# PLAN spec interpretation: the task-provided regex has a bug with
# the optional paren group consuming the year paren.  Simplified to
# match Author(s) (YYYY). Title or Author(s), YYYY. Title.
_CITATION_RE = re.compile(
    r'^[A-Z][a-zA-Z\-]+'
    r'(?:\s*&\s*[A-Z][a-zA-Z\-]+|\s+et\s+al\.?)?'
    r',?\s*'
    r'\(?(\d{4})\)?'
    r'\.?\s+'
    r'["*]?[A-Z]'
)

# G9 quantitative claim patterns (prose only; not inside code blocks or
# table rows -- see _extract_g9_anchors docstring).
# Pattern A: N weeks/months/days/hours/years/% (e.g. "12 weeks", "5%")
_QUANT_UNIT_RE = re.compile(
    r'\b\d{1,4}(?:\.\d+)?\s*(?:weeks?|months?|days?|hours?|years?|%)',
    re.IGNORECASE,
)
# Pattern B: $NNN[K/M/B] (e.g. "$500K", "$2.5M")
_DOLLAR_RE = re.compile(r'\$\d+(?:\.\d+)?[KMBkmb]?\b')
# Pattern C: Nx multiplier (e.g. "3x", "1.5x")
_MULT_RE = re.compile(r'\b\d+(?:\.\d+)?x\b')

# G9 anchor inline marker: [anchor: <content>]
_ANCHOR_RE = re.compile(r'\[anchor:\s*([^\]]+)\]', re.IGNORECASE)

# G9 downstream back-reference heuristic: if any of these phrases is within
# 80 chars of the quantitative claim, treat as a back-reference to the
# canonical declaration.
_BACK_REF_PHRASES = (
    'as discussed',
    'per reference class',
    'per derivation above',
    'per derivation below',
    'see l',     # line-reference prefix; intentionally short to match "see L100"
    'the canonical',
    'back-reference',
    'downstream',
)

# Chinese hedge word detection placeholder.
# v0.1 covers English only. Chinese hedge regex returns empty for
# non-English text. Extend in future version when Chinese plan
# support is needed.
# _HEDGE_ZH_RE = re.compile(r'...')  # placeholder

# ATX heading pattern -- used by multiple extraction functions.
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)')

# G9 design note: anchor search is per source-line, not per claim.
# All quantitative claims on the same line share the same look-ahead
# window (lineno .. lineno+2).  If an anchor appears anywhere in that
# window, ALL claims on lineno are credited to it.  This is intentional:
# one anchor can legitimately cover multiple claims in the same sentence.


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse(plan_text: str) -> ParsedPlan:
    """Parse a plan document and return a ParsedPlan.

    Args:
        plan_text: raw markdown text of the plan.

    Returns:
        ParsedPlan with all fields populated.
    """
    plan = ParsedPlan(raw_text=plan_text)
    lines = plan_text.splitlines()

    _extract_sections(plan, lines)
    _extract_sc_table(plan, lines)
    _extract_risks(plan, lines)
    _extract_hedge_words(plan, lines)
    _extract_citations(plan, lines)
    _extract_g9_anchors(plan, lines)

    return plan


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def _extract_sections(plan: ParsedPlan, lines: list[str]) -> None:
    """Walk lines and extract ParsedSection entries.

    Each ATX heading (# / ## / ###) starts a new section.  Body
    accumulation is INCLUSIVE: every open ancestor section also
    receives the line, so a parent section's body contains all its
    nested content.  This is intentional -- downstream checks search
    section bodies and expect full text under the heading.  If a check
    needs only direct-child content, it must filter by level.
    """
    # (level, heading_text, line_start_1indexed)
    stack: list[tuple[int, str, int]] = []
    # body lines accumulated per open section
    body_lines: dict[int, list[str]] = {}  # keyed by stack index

    def _close_section(idx: int, line_end: int) -> None:
        level, heading, line_start = stack[idx]
        body = '\n'.join(body_lines.get(idx, [])).strip()
        plan.sections[heading] = ParsedSection(
            heading=heading,
            level=level,
            body=body,
            line_start=line_start,
            line_end=line_end,
        )


    for lineno, line in enumerate(lines, 1):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()

            # Close all open sections with level >= current
            to_close = [i for i, (lv, _, _) in enumerate(stack)
                        if lv >= level]
            for i in sorted(to_close, reverse=True):
                _close_section(i, lineno - 1)
                stack.pop(i)
                body_lines.pop(i, None)

            # Open new section
            idx = len(stack)
            stack.append((level, heading_text, lineno))
            body_lines[idx] = []
        else:
            # Append line to ALL open sections' bodies
            for idx in range(len(stack)):
                body_lines.setdefault(idx, []).append(line)

    # Close any remaining open sections at end-of-document
    total_lines = len(lines)
    for i in range(len(stack) - 1, -1, -1):
        _close_section(i, total_lines)


# ---------------------------------------------------------------------------
# SC table extraction
# ---------------------------------------------------------------------------

def _extract_sc_table(plan: ParsedPlan, lines: list[str]) -> None:
    """Parse SC rows from any markdown table with SC-N / SC-Na first cell.

    Handles GFM-style pipe tables.  Extracts fail_condition when a column
    header contains "Fail Condition" (case-insensitive).

    PLAN spec interpretation: SC number is the numeric portion; for SC-2a
    we store number=2, suffix="a", full_id="SC-2a".
    """
    in_table = False
    fail_cond_col: int = -1
    name_col: int = -1
    body_col: int = -1

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped.startswith('|'):
            in_table = False
            fail_cond_col = -1
            name_col = -1
            body_col = -1
            continue

        cells = [c.strip() for c in stripped.split('|')]
        # Strip leading/trailing empty strings from split artefacts
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]

        if not cells:
            continue

        # Detect separator row (---|---| pattern)
        if all(re.match(r'^[-: ]+$', c) for c in cells):
            continue

        # Detect header row: first cell is exactly "sc" / "sc id" / etc.
        # Require exact match to avoid false-triggering on tables whose
        # first header is "scenario", "scope", "schedule", etc.
        first = cells[0].lower().strip() if cells else ''
        is_header_candidate = (
            first in ('sc', 'sc id', 'sc #', 'criterion', 'id', '#', 'no')
            or first.startswith('sc-')
        )

        if not in_table and is_header_candidate and len(cells) >= 2:
            # This is a header row
            in_table = True
            _header_cells = cells  # cells inspected via enumerate below
            for i, h in enumerate(cells):
                hl = h.lower()
                if 'fail' in hl and 'condition' in hl:
                    fail_cond_col = i
                elif hl in ('criterion', 'name', 'sc name', 'description'):
                    name_col = i
                elif hl in ('body', 'text'):
                    body_col = i
            continue

        if in_table and cells:
            m = _SC_ROW_RE.match(cells[0])
            if m:
                sc_num = int(m.group(1))
                sc_suffix = m.group(2) or ''
                raw_id = cells[0].strip()

                # Build name: use name_col if present; otherwise use the
                # second cell or the raw SC id
                if 0 <= name_col < len(cells):
                    sc_name = cells[name_col]
                elif len(cells) >= 2:
                    sc_name = cells[1]
                else:
                    sc_name = raw_id

                # Body: use body_col if present; else same as name
                if 0 <= body_col < len(cells):
                    sc_body = cells[body_col]
                else:
                    sc_body = sc_name

                # Fail condition
                fail_cond: str | None = None
                if 0 <= fail_cond_col < len(cells):
                    val = cells[fail_cond_col].strip()
                    fail_cond = val if val and val not in ('-', '--', 'N/A') \
                        else None

                plan.sc_table.append(ParsedSC(
                    number=sc_num,
                    suffix=sc_suffix,
                    full_id=raw_id,
                    name=sc_name,
                    body=sc_body,
                    fail_condition=fail_cond,
                    line=lineno,
                ))


# ---------------------------------------------------------------------------
# Risk register extraction
# ---------------------------------------------------------------------------

# Map subsection heading keywords to bucket names
_RISK_BUCKET_MAP = {
    'known risks': 'known',
    'known': 'known',
    'gray rhinos': 'gray_rhino',
    'gray rhino': 'gray_rhino',
    'grey rhinos': 'gray_rhino',
    'black swans': 'black_swan',
    'black swan': 'black_swan',
}


def _extract_risks(plan: ParsedPlan, lines: list[str]) -> None:
    """Extract ParsedRisk entries from Known/Gray Rhinos/Black Swans.

    Looks for ## Risks top-level section, then ### subsections per bucket.
    Within each bucket, parses table rows:
      - Known: description, probability, impact, mitigation
      - Gray Rhinos: description/gray_rhino, denial_reason, counter
      - Black Swans: description/black_swan, survival_plan
    """
    in_risks = False
    current_bucket: str | None = None

    in_table = False
    denial_col = -1
    survival_col = -1
    desc_col = -1

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        m_h = _HEADING_RE.match(stripped)
        if m_h:
            level = len(m_h.group(1))
            title = m_h.group(2).strip().lower()

            if level == 2 and 'risk' in title:
                in_risks = True
                current_bucket = None
                in_table = False
                continue

            if level > 2 and in_risks:
                # Sub-heading inside Risks section
                bucket_key = title
                if bucket_key in _RISK_BUCKET_MAP:
                    current_bucket = _RISK_BUCKET_MAP[bucket_key]
                    in_table = False
                    denial_col = -1
                    survival_col = -1
                    desc_col = -1
                    continue

            if level <= 2 and in_risks and 'risk' not in title:
                # Leaving the Risks section (same-or-higher level heading
                # that is not the Risks section itself).
                in_risks = False
                current_bucket = None
            # All heading lines are skipped for table extraction.
            continue

        if not in_risks or current_bucket is None:
            continue

        if not stripped.startswith('|'):
            in_table = False
            denial_col = -1
            survival_col = -1
            desc_col = -1
            continue

        cells = [c.strip() for c in stripped.split('|')]
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]

        if not cells:
            continue

        # Separator row
        if all(re.match(r'^[-: ]+$', c) for c in cells):
            continue

        # Header row detection: look for known column names
        first_lower = cells[0].lower() if cells else ''
        known_headers = {
            'risk', 'gray rhino', 'black swan', 'description',
            'risk description', 'risk / uncertainty',
        }
        is_header = first_lower in known_headers or (
            not in_table and any(
                h in ('probability', 'impact', 'mitigation',
                       'denial reason', 'denial_reason', 'counter',
                       'survival plan', 'survival_plan')
                for h in (c.lower() for c in cells)
            )
        )

        if not in_table and is_header:
            in_table = True
            _header_cells = cells  # cells inspected via enumerate below
            for i, h in enumerate(cells):
                hl = h.lower().replace(' ', '_').replace('/', '_')
                if 'denial' in hl:
                    denial_col = i
                elif 'survival' in hl:
                    survival_col = i
                elif hl in ('risk', 'description', 'gray_rhino',
                            'black_swan', 'risk_description'):
                    desc_col = i
            continue

        if in_table and cells:
            # Data row
            if 0 <= desc_col < len(cells):
                desc = cells[desc_col]
            else:
                desc = cells[0]

            denial: str | None = None
            if 0 <= denial_col < len(cells):
                val = cells[denial_col].strip()
                denial = val if val and val not in ('-', '--') else None

            survival: str | None = None
            if 0 <= survival_col < len(cells):
                val = cells[survival_col].strip()
                survival = val if val and val not in ('-', '--') else None

            plan.risks.append(ParsedRisk(
                bucket=current_bucket,
                description=desc,
                denial_reason=denial,
                survival_plan=survival,
            ))


# ---------------------------------------------------------------------------
# Hedge word detection (G4 Part A mechanical input)
# ---------------------------------------------------------------------------

def _extract_hedge_words(plan: ParsedPlan, lines: list[str]) -> None:
    """Detect hedge words in prose, skipping fenced code blocks.

    CRITICAL: uses fence-width-aware state machine.  Tracks
    fence width so that ```` ```` ```` blocks are not prematurely closed
    by ``` fences (CommonMark spec compliance).

    Also skips lines containing "G4 Probability Calibration" (self-
    reference exemption: the PLAN itself lists the hedge word set).

    Records: (1-based line number, lowercase hedge word).
    """
    in_code_block = False
    fence_width = ''
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        fence_match = re.match(r'^(`{3,})', stripped)
        if fence_match:
            fence = fence_match.group(1)
            if not in_code_block:
                in_code_block = True
                fence_width = fence
            elif fence == fence_width:
                in_code_block = False
                fence_width = ''
            continue
        if in_code_block:
            continue
        # Self-reference exemption
        if 'G4 Probability Calibration' in line:
            continue

        for m in _HEDGE_RE.finditer(line):
            plan.hedge_word_locations.append((lineno, m.group(0).lower()))


# ---------------------------------------------------------------------------
# Citation extraction (G8 Part A mechanical input)
# ---------------------------------------------------------------------------

def _extract_citations(plan: ParsedPlan, lines: list[str]) -> None:
    """Extract citation strings from External Voices section.

    Looks for any section whose heading contains "External Voices".
    Within that section, extracts list items (- or * prefixed lines)
    that match the citation regex.
    """
    in_ext_voices = False
    ext_voices_level = 0

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        m_h = _HEADING_RE.match(stripped)
        if m_h:
            level = len(m_h.group(1))
            title = m_h.group(2).strip()
            if 'External Voices' in title:
                in_ext_voices = True
                ext_voices_level = level
                continue
            # Leave section when hitting a heading at same or higher level
            if in_ext_voices and level <= ext_voices_level:
                in_ext_voices = False
            continue

        if not in_ext_voices:
            continue

        # Check list items
        if stripped.startswith(('-', '*', '+')):
            item = stripped.lstrip('-*+ ').strip()
            if _CITATION_RE.match(item):
                plan.citations.append(item)


# ---------------------------------------------------------------------------
# G9 anchor extraction
# ---------------------------------------------------------------------------

def _classify_anchor_type(anchor_text: str) -> str:
    """Classify anchor type from anchor content string.

    Classification rules:
      - starts with http or contains :// -> "url"
      - contains "prototype" -> "prototype"
      - contains "ref:" or "et al" -> "publication"
      - contains "in-plan-derivation" / "see table" / "section" /
        L<digit> / "above" / "below" -> "in_plan_derivation"
      - else -> "project_name"
    """
    at = anchor_text.lower()
    if anchor_text.startswith('http') or '://' in anchor_text:
        return 'url'
    if 'prototype' in at:
        return 'prototype'
    if 'ref:' in at or 'et al' in at:
        return 'publication'
    if (
        'in-plan-derivation' in at
        or 'in_plan_derivation' in at
        or 'see table' in at
        or 'section' in at
        or re.search(r'\bl\d+\b', at)
        or ' above' in at
        or ' below' in at
    ):
        return 'in_plan_derivation'
    return 'project_name'


def _is_back_reference(context: str) -> bool:
    """Return True if context contains a downstream back-reference phrase.

    Under the canonical-declaration convention: claims in downstream
    references to a canonical anchor do NOT need their own [anchor: ...].
    Any of the _BACK_REF_PHRASES within 80 chars of the claim suffices.
    """
    ctx_lower = context.lower()
    return any(phrase in ctx_lower for phrase in _BACK_REF_PHRASES)


def _find_all_quantitative_claims(line: str) -> list[str]:
    """Return all quantitative claim substrings found in a single line."""
    claims: list[str] = []
    seen: set[str] = set()
    for pattern in (_QUANT_UNIT_RE, _DOLLAR_RE, _MULT_RE):
        for m in pattern.finditer(line):
            text = m.group(0).strip()
            if text not in seen:
                claims.append(text)
                seen.add(text)
    return claims


def _extract_g9_anchors(plan: ParsedPlan, lines: list[str]) -> None:
    """Extract G9 feasibility anchors and unanchored quantitative claims.

    Processing rules:
    1. Skip fenced code blocks entirely (same in_code_block state machine
       as hedge-word detection).
    2. Skip table rows entirely: the Reference Class table IS the anchor
       source; requiring inline [anchor: ...] on each cell would be
       redundant.  G9 only checks prose paragraphs.
    3. For each quantitative claim in prose:
       a. Search the same line + next 2 lines for [anchor: ...].
       b. If found: record ParsedAnchor.
       c. If NOT found: check back-reference heuristic; if back-reference
          phrase within 80 chars -> skip; else record in
          quantitative_claims_without_anchor.

    Note: anchor extraction yields (claim, anchor_text, anchor_type, line)
    per ParsedAnchor schema.
    """
    in_code_block = False
    fence_width = ''
    total = len(lines)

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()

        # Fence-width-aware code block toggle (same logic as _extract_hedge_words)
        fence_match = re.match(r'^(`{3,})', stripped)
        if fence_match:
            fence = fence_match.group(1)
            if not in_code_block:
                in_code_block = True
                fence_width = fence
            elif fence == fence_width:
                in_code_block = False
                fence_width = ''
            continue
        if in_code_block:
            continue

        # Skip table rows (lines starting with |)
        if stripped.startswith('|'):
            continue

        claims = _find_all_quantitative_claims(line)
        if not claims:
            continue

        # Look-ahead window: same line + next 2 lines
        window_end = min(lineno + 2, total)  # lineno is 1-based
        window_lines = lines[lineno - 1:window_end]  # 0-indexed slice
        window_text = '\n'.join(window_lines)

        anchor_m = _ANCHOR_RE.search(window_text)

        for claim in claims:
            if anchor_m:
                anchor_text = anchor_m.group(1).strip()
                anchor_type = _classify_anchor_type(anchor_text)
                plan.anchors.append(ParsedAnchor(
                    claim_text=claim,
                    anchor_text=anchor_text,
                    anchor_type=anchor_type,
                    line=lineno,
                ))
            else:
                # Check back-reference: look at 80 chars around the claim
                idx = line.find(claim)
                if idx >= 0:
                    lo = max(0, idx - 80)
                    hi = min(len(line), idx + len(claim) + 80)
                    context = line[lo:hi]
                else:
                    context = line
                if _is_back_reference(context):
                    continue
                plan.quantitative_claims_without_anchor.append(
                    (lineno, claim)
                )
