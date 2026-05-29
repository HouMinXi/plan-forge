---
phase: 10
plan: review
status: PASS
cycles: 3
---
# Forge Review Result -- Phase 10

## Verdict: PASS (3 cycles, zero findings in final cycle)

Reviewed diff: `f2_duplicate_fact.py` three-way exclusion union +
two new test fixtures + two new unit tests.

---

## Cycle 1

### Pass 1 (qodo-review)

**F1 [MEDIUM]** -- `parsed.raw_text.splitlines()` has no None guard.
If `ParsedPlan.raw_text` is ever `None` (not initialized), this raises
`AttributeError` at runtime. Original code only used `parsed.sections`
(a list) which would also crash if None, suggesting the `ParsedPlan`
contract may guarantee initialization -- but the new field access is not
defended.

**F2 [LOW]** -- `"signed-off-by"` in `_STRUCTURAL_WORDS` is dead code.
`_CAP_TOKEN_RE = r'\b[A-Z][A-Za-z0-9_-]{2,}\b'` only matches tokens
starting with an uppercase letter. `"signed-off-by"` is all-lowercase
and will never appear as an n-gram token, so this entry in the frozenset
never matches anything. The accompanying comment is misleading because
the entry has no effect on filtering.

### Pass 2 (code-review-expert)

**F3 [LOW]** -- `signoff_words` extraction does not filter `len(w) < 3`.
`_extract_ngrams` uses `_CAP_TOKEN_RE` which enforces a minimum 3-character
token (the `{2,}` suffix requires at least 2 chars after the first, giving
a total minimum of 3). Tokens shorter than 3 characters (e.g. `"Li"`, `"Yu"`)
can enter `signoff_words` but can never appear in any n-gram's word set.
They are redundant entries that add noise without affecting correctness.
The plan specifies a >= 3 char filter; the implementation omits it.

**Positive findings:**
- Three-way union `_STRUCTURAL_WORDS | signoff_words | heading_words`
  correctly preserves Phase 8's `heading_words` guard (superset relation
  guarantees any n-gram filtered by `heading_words` alone is still
  filtered by `exclusion`).
- `_SIGNOFF_RE` handles case variants and missing `<email>` sections
  correctly.

### Pass 3 (adversarial-qe)

- F1 confirmed: `None.splitlines()` raises `AttributeError`.
- Non-ASCII scan: all `+` lines in the diff are pure ASCII. No Unicode
  smart quotes, em-dashes, ellipsis characters, or arrows detected.
- AI-smell scan: no plan-ref comments, no task IDs in source code.
  Comments read as normal engineering prose.
- Edge case: empty `raw_text = ""` -- `"".splitlines()` returns `[]`,
  loop does not execute, `signoff_words` remains empty. Correct.
- Fixture `f2_signoff_fp.md`: `signoff_words = {"minxi", "hou"}`.
  Repeated bigram `"minxi hou"` has word set subset of signoff_words.
  Filtered correctly.
- Fixture `f2_structural_fp.md`: words like `Run`, `Expected`, `Pass`,
  `Write`, `Create`, `Step` all match `_CAP_TOKEN_RE` (>= 3 chars) and
  their lowercase forms are in `_STRUCTURAL_WORDS`. All resulting bigrams
  are subsets of `_STRUCTURAL_WORDS`. Filtered correctly.

---

## Cycle 2

### Pass 1 (qodo-review) -- re-verification

**F1 re-evaluated:** `parsed.sections` is also accessed without a None
guard in the original code. This suggests `ParsedPlan` has an established
contract that all fields are initialized before `check()` is called.
F1 is downgraded to INFO -- a defensive-programming recommendation rather
than a confirmed bug. However, the new `raw_text` access is the first use
of this field in `check()`, so the risk level depends entirely on whether
`ParsedPlan.__init__` guarantees `raw_text` is set to at least `""`.

**F2 re-confirmed:** `"signed-off-by"` remains dead code in the frozenset.
No correctness impact; purely a clarity issue.

**F3 re-confirmed:** Short-token redundancy in `signoff_words` is harmless.
The n-gram word-set subset check is only ever satisfied for words that came
from `_CAP_TOKEN_RE` (>= 3 chars), so short words in `signoff_words` have
no effect.

No new findings in Pass 1 Cycle 2.

### Pass 2 (code-review-expert)

- Thread safety: `exclusion` is constructed locally inside `check()`
  each invocation. `_STRUCTURAL_WORDS` is a module-level `frozenset`
  (immutable). No shared mutable state. Thread-safe.
- `flagged[:_FINDING_CAP]` truncation before filtering: pre-existing
  behavior, out of scope for this diff.
- False-negative risk from `signoff_words`: if author name tokens
  match technical vocabulary, those tokens could suppress genuine findings.
  Acceptable risk given the improbability and the `<email>` stripping that
  already reduces captured content to only the human name portion.

No new findings in Pass 2 Cycle 2.

### Pass 3 (adversarial-qe)

- No new findings.
- `_SIGNOFF_RE` boundary test: extra spaces and missing `<email>` both
  handled correctly by `strip()` + `split()` after `re.sub`.

---

## Cycle 3

### Pass 1 (qodo-review) -- final

F1 downgraded to INFO: consistent with `parsed.sections` usage pattern;
`ParsedPlan` contract likely guarantees field initialization. No action
required unless `ParsedPlan` documentation marks `raw_text` as `Optional[str]`.

F2 and F3 remain LOW, both non-blocking, both with zero correctness impact.

Zero new findings.

### Pass 2 (code-review-expert) -- final

No SOLID violations, no correctness bugs, no security issues, no missing
invariants that would affect behavior. All three findings from prior cycles
are style/consistency observations only.

Zero new findings.

### Pass 3 (adversarial-qe) -- final

Non-ASCII re-scan: confirmed clean.
AI-smell re-scan: confirmed clean.
Behavioral correctness: three-way union is mathematically correct and
preserves Phase 8 semantics.

**Zero findings -- exit criteria met.**

---

## Summary of All Findings

| ID | Severity | Location | Description | Correctness Impact |
|----|----------|----------|-------------|-------------------|
| F1 | INFO | `check()` line 43 | `parsed.raw_text.splitlines()` -- no None guard; depends on ParsedPlan contract | None if contract holds |
| F2 | LOW | `_STRUCTURAL_WORDS` line 29 | `"signed-off-by"` unreachable by `_CAP_TOKEN_RE`; dead set member | None |
| F3 | LOW | `check()` line 47 | `signoff_words` does not filter len < 3; plan specifies >= 3 char filter | None (short tokens never appear in n-gram word sets) |

No CRITICAL or HIGH findings. No MEDIUM findings (F1 downgraded to INFO
in Cycle 3 after accounting for ParsedPlan contract evidence).
