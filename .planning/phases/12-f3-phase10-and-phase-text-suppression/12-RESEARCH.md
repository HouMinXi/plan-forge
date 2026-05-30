# Phase 12 Research: F3 Phase 10+ Subplan ID and Phase-Text Self-Reference

**Phase:** 12
**Confidence:** HIGH (all claims verified by direct Python re execution and fixture inspection)

## 1. Regex Correctness: ISO Date Protection

Proposed regex: `r'(?<!\d-)\b(?:0[1-9]|[1-9]\d)-\d{2}\b'`

Trace on `'2026-10-02'`:
- Candidate at position 5 (`'1'` of `10-02`).
- Lookbehind `(?<!\d-)` reads `s[3:5]` = `'6-'`: digit + hyphen. Lookbehind fires, match rejected.
- Result: **no match** (correct).

Verified match results:

| Input | Current matches | Proposed matches |
|-------|----------------|-----------------|
| `'10-02'` | `[]` | `['10-02']` |
| `'2026-10-02'` | `[]` | `[]` |
| `'2026-10-02 references 10-02'` | `[]` | `['10-02']` |
| `'09-05'` | `['09-05']` | `['09-05']` |
| `'2026-12-31'` | `[]` | `[]` |
| `'a-10-02'` | `[]` | `['10-02']` (letter-hyphen not blocked by lookbehind) |

Edge note: `'10-10-02'` matches `'10-10'` (Phase 10, Plan 10). Pre-existing behavior
(same applies to `'09-10-02'` with current regex). Not introduced by Phase 12.

## 2. Existing Test Compatibility: Zero Tests Break

All 10 existing test functions analyzed against all 7 fixtures. None contain a bare
Phase 10+ ID outside an ISO date. Extended regex changes nothing for any existing fixture.

| Test | Fixture | Assert style | Phase 12 impact |
|------|---------|-------------|-----------------|
| `test_f3_pass_fixture` | `f3_pass.md` | `findings == []` | None (T05/T06 only) |
| `test_f3_fail_fixture` | `f3_fail.md` | `check_id in ids` | None (T08 + "phase 3") |
| `test_f3_severity` | `f3_fail.md` | severity == HIGH | None |
| `test_f3_edge_case_insensitive_exemption` | inline | `findings == []` | None ("Phase-1" text) |
| `test_f3_edge_audit_notes_exemption` | inline | `findings == []` | None (T09 only) |
| `test_f3_self_ref_silent` | `f3_self_ref.md` | `"02-01" not in findings` | None |
| `test_f3_date_fragment_silent` | `f3_date_nofire.md` | `findings == []` | None (ISO dates only) |
| `test_f3_cross_ref_still_fires` | `f3_cross_ref_fires.md` | `"02-03" in messages` | None |
| `test_f3_dedup_fires_once` | `f3_dedup_fp.md` | `len == 1` for Phase 8 | None |
| `test_f3_own_id_suppressed_via_frontmatter` | `f3_own_id_fp.md` | `"08-02" not in findings` | None |

## 3. Fixture Inventory

Seven existing fixtures:
- `f3_pass.md`: T05/T06 in References, 0 findings expected.
- `f3_fail.md`: T08 + "phase 3" in body, no References section, findings expected.
- `f3_self_ref.md`: heading `# 02-01`, body repeats "02-01", own-ID suppressed via heading scan.
- `f3_date_nofire.md`: only ISO dates in body, all fragments suppressed.
- `f3_cross_ref_fires.md`: heading `# 02-01`, body references `02-03` (different ID, fires).
- `f3_dedup_fp.md`: "Phase 8" six times, no frontmatter, produces exactly 1 finding.
- `f3_own_id_fp.md`: `phase: "08"`, `plan: "02"` in frontmatter, body references "08-02", 0 findings.

Three new fixtures required:

**`f3_phase10_cross_ref.md`** (Change A RED state):
No frontmatter, bare `10-02` in body, no audit notes.
- Before fix: 0 findings (regex miss = false negative)
- After fix: 1 F3 HIGH finding
- Test: `assert len(findings) == 1 and "10-02" in findings[0].message`

**`f3_phase10_own_id_fp.md`** (Change A own-ID regression):
`phase: 10` and `plan: 2` in frontmatter, body references `10-02`.
- After fix: 0 F3 findings (own-ID suppression working end-to-end)
- Test: `assert findings == []`

**`f3_phase_text_fp.md`** (Change B combined FP suppression + anti-gutting):
`phase: 8` in frontmatter (no `plan:` field), body has "Phase 8" and "Phase-8" (suppressed),
AND "Phase 9" without audit notes (still fires).
- After fix: exactly 1 F3 HIGH for "Phase 9", 0 for "Phase 8"/"Phase-8"
- Test: `assert len(findings) == 1 and any("Phase 9" in f.message for f in findings)`

## 4. Phase-Text Token Verification

`_PHASE_RE = re.compile(r'\bphase[-\s]\d+\b', re.IGNORECASE)` -- `[-\s]` matches both hyphen and space.

| Input | `m.group(0)` | `.lower()` |
|-------|-------------|-----------|
| `'Phase 8'` | `'Phase 8'` | `'phase 8'` |
| `'Phase-8'` | `'Phase-8'` | `'phase-8'` |
| `'phase 08'` | `'phase 08'` | `'phase 08'` |
| `'phase-08'` | `'phase-08'` | `'phase-08'` |

D-04 tokens for `phase: 8` (`phase_num='08'`, `int('08')=8`): 4 distinct tokens.
For `phase: 10` (`phase_num='10'`, `int('10')=10`): 2 distinct tokens (padded==unpadded
for two-digit numbers, set absorbs duplicates). Correct and harmless.

## 5. Test Pattern Reference

RED state:
```python
findings = f3_cross_plan_invariant.check(parsed)
assert len(findings) == 1
assert "10-02" in findings[0].message
```

FP suppression:
```python
findings = f3_cross_plan_invariant.check(parsed)
assert findings == []
```

Combined (some suppressed, some fire):
```python
findings = f3_cross_plan_invariant.check(parsed)
assert len(findings) == 1
assert any("Phase 9" in f.message for f in findings)
assert all("Phase 8" not in f.message for f in findings)
```

## 6. Risks and Planning Additions

### CRITICAL: Stale comment must be removed in Plan 12-02

Lines 39-42 of `f3_cross_plan_invariant.py` currently contain:
```
# Note: Phase 10+ IDs (two-digit phase numbers like 10-02) are not matched
# by _SUBPLAN_RE in document body, so frontmatter extraction adds them to
# the verified set but suppression has no practical effect on body scanning.
# Extending the subplan pattern to cover Phase 10+ is deferred.
```

After the fix, this comment is factually wrong. Plan 12-02 MUST include an
explicit step to remove this 4-line comment block. Forge review will catch it.

### LOW risks (no action needed)

- `10-00` now matches (plan number `00`). Pre-existing for `01-00`. No real plan uses `00`.
- `f3_dedup_fp.md` has no frontmatter; D-04/D-05 never runs for it. Unaffected.

## Summary for Planner

Wave structure confirmed:
- **12-01**: worktree setup + 3 new fixtures + RED test stubs (will fail before fix)
- **12-02**: `_SUBPLAN_RE` constant change + D-04/D-05 phase-text block + remove stale comment (lines 39-42) + bite test
- **12-03**: forge review (separate sub-session) + merge + worktree cleanup

## RESEARCH COMPLETE
