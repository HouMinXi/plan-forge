"""F6: Preamble-vs-body diff.

When an orchestrator preamble is provided, checks whether facts stated
in the preamble are also present in the plan body.  Uses substring
matching plus a 5-token sequence fallback heuristic.
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Sentence splitter: split on terminal punctuation followed by whitespace
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

# Minimum sentence length to evaluate (chars)
_MIN_SENTENCE_LEN = 20

# Minimum token subsequence length for the fallback check
_SEQ_LEN = 5

# Maximum findings per plan
_FINDING_CAP = 10


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def _tokens(text: str) -> list[str]:
    """Split text into lowercase whitespace-separated tokens."""
    return text.lower().split()


def _token_seq_present(sentence_tokens: list[str], body_tokens: list[str]) -> bool:
    """Return True if any contiguous 5-token subseq of sentence is in body."""
    if len(sentence_tokens) < _SEQ_LEN:
        return False
    # Build set of body 5-grams for O(n) lookup
    body_grams: set[tuple[str, ...]] = set()
    for i in range(len(body_tokens) - _SEQ_LEN + 1):
        body_grams.add(tuple(body_tokens[i:i + _SEQ_LEN]))
    for i in range(len(sentence_tokens) - _SEQ_LEN + 1):
        if tuple(sentence_tokens[i:i + _SEQ_LEN]) in body_grams:
            return True
    return False


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check preamble facts against plan body.

    Args:
        parsed: ParsedPlan to inspect.
        preamble: orchestrator preamble string (keyword arg).

    Returns:
        [] if preamble is None or empty; otherwise list of F6 findings.
    """
    preamble: str | None = kwargs.get('preamble', None)

    if preamble is None or preamble.strip() == '':
        return []

    # Extract sentences from preamble
    raw_sentences = _SENTENCE_SPLIT_RE.split(preamble.strip())
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) >= _MIN_SENTENCE_LEN]

    if not sentences:
        return []

    norm_body = _normalize(parsed.raw_text)
    body_tokens = _tokens(parsed.raw_text)

    # Accumulate (sentence_len, finding) so we can sort by original length.
    # SUBSPEC: "top 10 by sentence length" -- sort before message is truncated to 80 chars.
    pending: list[tuple[int, Finding]] = []

    for idx, s in enumerate(sentences):
        norm_s = _normalize(s)
        # Primary check: normalized sentence is substring of normalized body
        if norm_s in norm_body:
            continue
        # Fallback: 5-token sequence check
        s_tokens = _tokens(s)
        if _token_seq_present(s_tokens, body_tokens):
            continue
        pending.append((len(s), Finding(
            check_id="F6.preamble_only_fact",
            severity=Severity.LOW,
            location=f"preamble:sentence:{idx}",
            message=(
                f"fact from preamble not present in plan body:"
                f" {s[:80]!r}"
            ),
            fix_hint=(
                "incorporate this fact into the relevant section of the"
                " plan, or document why it is intentionally omitted"
            ),
        )))

    # Sort by original sentence length descending (SUBSPEC: top 10 by sentence length)
    pending.sort(key=lambda x: -x[0])
    return [f for _, f in pending[:_FINDING_CAP]]
