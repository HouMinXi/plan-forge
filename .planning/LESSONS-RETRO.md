# LESSONS-RETRO: Retroactive Audit of Forge Phase 2 Plans

Status: TEMPLATE -- populated by T34.

---

## Purpose

SC-3 retroactive audit: measure how well plan-forge (as of a stable release) would
have caught problems that actually occurred in archived forge Phase 2 plans.

Coverage metric: problems_caught / total >= 60% (SC-3 ship gate).

---

## Method

- Audited plans: 02-01-PLAN.md through 02-06-PLAN.md (archived forge Phase 2 sub-plans)
- Independent ground truth: forge 02-LEARNINGS.md problem list (pre-existing, not
  derived from plan-forge output)
- Runner: tools/retroactive_audit.py (T20 provides discovery; T34 adds check() calls)

---

## Per-Plan Results

| Plan       | plan-forge findings | Matched 02-LEARNINGS problems | Missed |
|------------|---------------------|-------------------------------|--------|
| 02-01      | (T34)               | (T34)                         | (T34)  |
| 02-02      | (T34)               | (T34)                         | (T34)  |
| 02-03      | (T34)               | (T34)                         | (T34)  |
| 02-04      | (T34)               | (T34)                         | (T34)  |
| 02-05      | (T34)               | (T34)                         | (T34)  |
| 02-06      | (T34)               | (T34)                         | (T34)  |

---

## SC-3 Coverage

| Metric      | Value  |
|-------------|--------|
| Total known problems (from 02-LEARNINGS.md) | (T34) |
| Problems caught by plan-forge               | (T34) |
| Coverage (caught / total)                   | (T34) |

Target: >= 60%. Fail condition: < 60%.

---

## Findings / Lessons

(T34 fills this section after completing the audit run.)
