"""F8: Plan consistency check.

Two sub-checks, each deterministic (no LLM):

F8.A -- Unsupported capability claim (PRIMARY, required for v0.1.0):
  The plan asserts a real-world effect ("catches real bugs", "validates
  against production", etc.) but every evidence/tests/fixtures section
  references only mock, stub, or synthetic data.  Such a plan overstates
  what its test suite actually exercises.

  Algorithm:
    1. Collect "claim sentences": prose lines that contain at least one
       capability claim keyword (from _CLAIM_KEYWORDS) outside fenced
       code blocks.
    2. Collect "evidence text": the body of any section whose heading
       matches _EVIDENCE_HEADING_RE (Tests, Fixtures, Verification,
       Evidence, Test Plan, Validation).
    3. If no claim sentences -> pass (nothing to check).
    4. If no evidence sections -> pass (the check cannot prove absence;
       other gates cover missing sections).
    5. Compute synthetic_only: True when evidence text contains at least
       one synthetic-data token (_MOCK_TOKENS) AND zero real-evidence
       anchors (_REAL_ANCHORS).
    6. Emit HIGH finding only when synthetic_only is True AND at least
       one claim sentence is present.

  Precision safeguards:
    - Claim keyword matching requires a word boundary on both sides,
      preventing "validate" from matching "invalidate".
    - "example" is in _MOCK_TOKENS but exempt when it appears in
      "for example" (introducing a real illustration, not a fake).
    - A plan whose evidence section mentions BOTH mock data AND a real
      data path (e.g. "real", "production", "live", "actual") is
      treated as grounded and does NOT fire.

F8.B -- Internal contradiction (SECONDARY, circuit breaker applies):
  Prose asserts X and an immediately adjacent fenced code/pseudocode
  block shows not-X.  Only the most mechanically unambiguous pair is
  targeted: "returns a list" / code block whose first non-blank,
  non-comment statement is a return of a dict/set/scalar literal.

  Circuit breaker: if the heuristic cannot achieve high precision on
  the synthetic FP fixtures (see tests), this sub-check is OMITTED
  from v0.1.0.  The note "contradiction detection deferred to v0.1.x"
  remains in the output.

  After validation: F8.B was DEFERRED.  The contradiction heuristic
  produced false positives on the agreed FP fixtures.  Only F8.A
  ships in v0.1.0.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# F8.A: Unsupported capability claim

# Capability claim phrases -- must be a real-world-effect claim.
# Each pattern is compiled with word boundaries for precision.
_CLAIM_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(
        r'\bcatches?\s+real\s+bugs?\b', re.IGNORECASE
    ),
    re.compile(
        r'\bvalidates?\s+against\s+production\b', re.IGNORECASE
    ),
    re.compile(
        r'\bworks?\s+on\s+real\s+code\b', re.IGNORECASE
    ),
    re.compile(
        r'\bdetects?\s+real\s+bugs?\b', re.IGNORECASE
    ),
    re.compile(
        r'\bexercises?\s+real\s+(code|system|data)\b', re.IGNORECASE
    ),
    re.compile(
        r'\bverifies?\s+against\s+(production|live)\b', re.IGNORECASE
    ),
    re.compile(
        r'\btests?\s+with\s+real\s+(data|code|system)\b', re.IGNORECASE
    ),
    re.compile(
        r'\bfinds?\s+real\s+bugs?\b', re.IGNORECASE
    ),
)

# Headings that indicate an evidence/tests section.
_EVIDENCE_HEADING_RE = re.compile(
    r'\b(tests?|fixtures?|verification|evidence|test\s+plan'
    r'|validation|test\s+suite|testing)\b',
    re.IGNORECASE,
)

# Tokens that indicate the evidence section uses only synthetic data.
# Checked as case-insensitive whole-word matches in the evidence text.
_MOCK_TOKENS: tuple[str, ...] = (
    'mock', 'stub', 'stub-', 'synthetic', 'fake', 'dummy',
    'placeholder', 'fixture', 'example',
)

# Phrase that makes "example" benign (it introduces a real illustration).
_EXAMPLE_EXEMPT_RE = re.compile(
    r'\bfor\s+example\b', re.IGNORECASE
)

# Real-evidence anchors: if any appear in the evidence section the
# plan is treated as grounded.
_REAL_ANCHOR_TOKENS: tuple[str, ...] = (
    'real', 'production', 'live', 'actual', 'codebase',
    'repository', 'repo', 'corpus', 'ground.truth',
)

# Maximum findings from F8.A per plan (normally at most one, cap for safety).
_FINDING_CAP_A = 5


def _has_capability_claim(line: str) -> tuple[bool, str]:
    """Return (True, matched_text) if line contains a capability claim."""
    for pat in _CLAIM_PATTERNS:
        m = pat.search(line)
        if m:
            return True, m.group(0)
    return False, ''


def _is_mock_evidence_only(evidence_text: str) -> bool:
    """Return True when evidence text has synthetic tokens but no real ones.

    Applies the "for example" exemption for the 'example' token.
    """
    text_lower = evidence_text.lower()

    has_mock = False
    for token in _MOCK_TOKENS:
        # Use word-boundary-like check: surrounded by non-alpha characters.
        pattern = r'(?<![a-z])' + re.escape(token) + r'(?![a-z])'
        if re.search(pattern, text_lower):
            if token == 'example':
                # Exempt "for example" usages -- count only residual hits.
                residual = _EXAMPLE_EXEMPT_RE.sub('', evidence_text)
                if not re.search(
                    r'(?<![a-z])example(?![a-z])',
                    residual.lower(),
                ):
                    continue
            has_mock = True
            break

    if not has_mock:
        return False

    for anchor in _REAL_ANCHOR_TOKENS:
        pattern = r'(?<![a-z])' + re.escape(anchor) + r'(?![a-z])'
        if re.search(pattern, text_lower):
            return False

    return True


def _collect_evidence_text(parsed: ParsedPlan) -> str:
    """Return concatenated body text of all evidence-type sections.

    Only considers sections at level 2 or deeper (h2/h3/...) to avoid
    matching a document title that happens to contain a keyword like
    'Evidence' or 'Tests'.  Top-level (h1) section bodies are inclusive
    and would pull in all nested content, defeating the purpose.
    """
    parts: list[str] = []
    for heading, section in parsed.sections.items():
        if section.level >= 2 and _EVIDENCE_HEADING_RE.search(heading):
            parts.append(section.body)
    return '\n'.join(parts)


def _check_capability_claim(parsed: ParsedPlan) -> list[Finding]:
    """Run F8.A: unsupported capability claim sub-check."""
    findings: list[Finding] = []

    # Collect claim lines from prose (skip fenced code blocks).
    in_code_block = False
    fence_width = ''
    claim_lines: list[tuple[int, str, str]] = []  # (lineno, line, matched)

    for lineno, line in enumerate(parsed.raw_text.splitlines(), 1):
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

        found, matched = _has_capability_claim(line)
        if found:
            claim_lines.append((lineno, line, matched))

    if not claim_lines:
        return []

    evidence_text = _collect_evidence_text(parsed)
    if not evidence_text.strip():
        # No evidence sections present; other gates (G1, G7) cover that.
        return []

    if not _is_mock_evidence_only(evidence_text):
        return []

    # Emit one finding per distinct claim line, capped.
    seen_claims: set[str] = set()
    for lineno, _line, matched in claim_lines:
        if matched.lower() in seen_claims:
            continue
        seen_claims.add(matched.lower())
        if len(findings) >= _FINDING_CAP_A:
            break
        findings.append(Finding(
            check_id='F8.A.unsupported_capability_claim',
            severity=Severity.HIGH,
            location=f'line:{lineno}',
            message=(
                f'plan claims real-world effect ({matched!r}) but'
                f' evidence/tests section references only mock/'
                f'stub/synthetic data'
            ),
            fix_hint=(
                'either remove the real-world claim, or add tests that'
                ' run against real/production/live data and document'
                ' the grounding in the evidence section'
            ),
        ))

    return findings


# Public entry point

def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Run F8 plan-consistency checks.

    F8.A (unsupported capability claim) fires when the plan makes
    real-world-effect claims but the evidence/tests section references
    only mock or synthetic data.

    F8.B (internal contradiction) is deferred to v0.1.x: the
    contradiction heuristic could not meet the precision bar required
    by the circuit breaker across the agreed FP fixture set.

    Args:
        parsed: ParsedPlan produced by parser.parse().

    Returns:
        List of F8 findings.
    """
    return _check_capability_claim(parsed)
