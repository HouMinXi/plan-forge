---
name: plan-forge
description: "Review a plan document with plan-forge gates and human-in-loop
  arbitration. Use when the user runs /plan-forge <path> or asks to check a
  plan/roadmap/spec for epistemic and mechanical quality with arbitration."
---

# plan-forge skill

Invocation: /plan-forge <path-to-plan.md>

## Steps

1. Resolve the plan path from the user's invocation.

2. Check corpus activation: if PLAN_FORGE_CORPUS_URL is unset, warn the user
   that arbitration verdicts will not be persisted, and ask whether to proceed
   analysis-only.

3. Run analysis:
   python -m plan_forge.adapters.skill.runner analyze \
     --plan-path <path> --arbitration-mode on_split_evidence_rich

4. Parse the JSON response. Present the verdict summary
   (engineering / epistemic / summary).

5. For each entry in arbitration_candidates:
   - Show the bundle_text to the user.
   - Use AskUserQuestion to collect a verdict from exactly four options:
     verified / unverified / deferred / abstain
   - Collect an optional rationale (free text via the notes/Other field).

6. For each answered candidate (verdict != abstain or deferred is fine to
   capture too), run:
   python -m plan_forge.adapters.skill.runner capture \
     --session-file <session_file> --index <i> \
     --verdict <verdict> --rationale "<rationale>"

7. Summarize: the gate verdict plus how many arbitration verdicts were captured.

## Requirements

- plan-forge must be installed: pip install -e .
- For capture to persist verdicts: PLAN_FORGE_CORPUS_URL must be set.
- To make /plan-forge invocable, symlink or copy this file to
  ~/.claude/skills/plan-forge/SKILL.md.
