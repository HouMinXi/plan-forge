# T20 SUBSPEC: LESSONS-RETRO scaffold + retroactive_audit runner skeleton

Status: draft for subagent implementation.
Depends on: T05 skeleton (stub exists), T15 library check().
Scope: pre-audit INFRASTRUCTURE only. The actual audit (running check on each
plan, comparing to 02-LEARNINGS.md, computing SC-3 coverage) is T34, NOT T20.

## 1. tools/retroactive_audit.py (replace the stub)
Purpose: discovery + iteration scaffold for the T34 retroactive audit. T20 makes
the runner able to ENUMERATE the archived forge Phase 2 sub-plans; it does NOT
run plan_forge.check and does NOT compute coverage (both are T34).

Exact API:
    def discover_plans(base_dir, pattern="02-0*-PLAN.md") -> list[Path]:
        """Return SORTED archived plan paths under base_dir matching pattern.
        base_dir example:
        ~/code/forge/.planning/milestones/v2.0-phases/02-state-machine-rewrite
        Returns [] if base_dir is not an existing directory."""

    def main(argv=None) -> int:
        # argparse: positional base_dir, optional --pattern (default above).
        # discover; if empty -> print a 'no plans found' message, return 1.
        # else print each path, then a summary line noting audit logic is T34
        # scope, return 0.

Constraints:
- Module imports stay light: from __future__ import annotations; argparse;
  from pathlib import Path. Do NOT import plan_forge.check here (T34 adds it).
- base_dir is a PARAMETER. Do NOT hardcode ~/code/forge anywhere (CI/portability).
- DEFAULT pattern "02-0*-PLAN.md" matches the real forge naming
  (02-01-PLAN.md .. 02-06-PLAN.md, confirmed present).
- discover_plans returns sorted() output for deterministic ordering.
- `if __name__ == "__main__": raise SystemExit(main())`.

## 2. .planning/LESSONS-RETRO.md (new -- empty TEMPLATE)
A markdown template that T34 will populate. It must clearly mark every data slot
as "(T34)" so no one mistakes the empty template for a completed audit. Sections:
- Title + "Status: TEMPLATE -- populated by T34."
- Purpose: SC-3 retroactive audit; coverage = problems_caught / total >= 60%.
- Method: audited plans 02-01..02-06; independent ground truth = the forge
  02-LEARNINGS.md problem list; runner = tools/retroactive_audit.py.
- A per-plan results table (rows 02-01..02-06; columns: plan-forge findings /
  matched 02-LEARNINGS problems / missed) with every cell "(T34)".
- SC-3 coverage block (total / caught / coverage %), cells "(T34)",
  note "target >= 60%; fail-condition < 60%".
- A "Findings / lessons (T34 fills)" section.
ASCII only. Do NOT invent audit numbers -- it is a template.

## 3. Tests: tests/unit/test_retroactive_audit.py
- test_discover_finds_and_sorts: create a tmp dir with 02-01-PLAN.md,
  02-03-PLAN.md, 02-02-PLAN.md and an unrelated file; assert discover returns
  the three in sorted order and excludes the unrelated file.
- test_discover_missing_dir: non-existent dir -> [].
- test_main_no_plans_returns_1: empty tmp dir -> main([str(dir)]) returns 1.
- test_main_lists_plans_returns_0: tmp dir with 2 plans -> main returns 0;
  capsys shows both paths.
- test_default_pattern_matches_forge_naming: fnmatch("02-01-PLAN.md",
  DEFAULT pattern) is True; fnmatch("README.md", pattern) is False.

## 4. Non-goals (T20)
- Do NOT run plan_forge.check / compute SC-3 coverage (T34).
- Do NOT read the real ~/code/forge tree in tests (use tmp fixtures).
- Do NOT touch any src/plan_forge/ check module.
