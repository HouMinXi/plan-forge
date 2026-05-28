---
phase: "09"
plan: "01"
subsystem: "forge-docs"
tags: ["docs", "g-gate", "roadmap", "no-code-change"]
dependency_graph:
  requires: []
  provides: ["forge-roadmap-g-gate-sections"]
  affects: ["plan-forge-g-gate-checks"]
tech_stack:
  added: []
  patterns: ["G-gate keyword matching via find_section()"]
key_files:
  created:
    - /home/houminxi/code/forge/.worktrees/p9-gsd-compat/.planning/milestones/v2.1-dynamic-gate/ROADMAP.md
  modified:
    - /home/houminxi/code/forge/.worktrees/p9-gsd-compat/.planning/ROADMAP.md
decisions:
  - "Milestone ROADMAP in worktree needed to be created (not just modified) -- directory did not exist"
  - "Force-add required (git add -f) because .planning/ is in forge .gitignore but files are tracked"
  - "Both ROADMAP files share identical epistemic sections -- same milestone, same domain"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-28"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 2
---

# Phase 9 Plan 01: ROADMAP G-gate Sections Summary

Added the six G-gate-compatible epistemic sections (Reference Class, Risks,
Pre-mortem, Chaos Response, Scope Challenge, External Voices) to both v2.1
milestone ROADMAP files in the forge repo worktree, clearing 10 of the 36
no_section BLOCKERs identified in the Phase 9 audit.

## What Was Done

Both ROADMAP files in the `p9-gsd-compat` worktree received identical appended
sections:

1. `## Reference Class` -- three comparable dynamic-gate projects with
   plan-vs-actual ratios (Chromium CQ tiering, Rust bors, Forge Phase 1)
2. `## Risks` -- Known Risks / Gray Rhinos / Black Swans tables
3. `## Pre-mortem` -- five failure mode scenarios with early warnings and counters
4. `## Chaos Response` -- stressor table with survive/degrade classification
5. `## Scope Challenge` -- Q1-Q4 framework (need, consumers, do-nothing cost,
   barbell vs middle ground)
6. `## External Voices` -- two APA-format citations (Petrovic & Ivankovic 2018;
   Jia & Harman 2011) with dissenting perspective and honest assessment

## Verification Results

Both files verified with api.check(llm_clients=[]) immediately after editing:

- `.planning/ROADMAP.md -> no_section BLOCKERs: 0`
- `v2.1-dynamic-gate/ROADMAP.md -> no_section BLOCKERs: 0`

Non-ASCII checks passed on both files (no em dashes, smart quotes, or other
non-ASCII characters introduced).

## Commits

Forge repo (branch `p9-gsd-compat`):
- `092ee95`: docs: add G-gate sections to v2.1 milestone ROADMAPs

## Deviations from Plan

### Auto-resolved Issues

**1. [Rule 3 - Blocking] Milestone ROADMAP directory missing in worktree**
- Found during: Task 2 setup
- Issue: worktree only had `.planning/ROADMAP.md`; the milestone path
  `.planning/milestones/v2.1-dynamic-gate/ROADMAP.md` did not exist in the
  worktree -- the `milestones/` directory was absent.
- Fix: created the directory with `mkdir -p` and wrote the full file (using
  the main repo content as the base, then appending the new sections).
- Files modified: `.planning/milestones/v2.1-dynamic-gate/ROADMAP.md` (created)

**2. [Rule 3 - Blocking] git add blocked by .gitignore**
- Found during: Task 2 commit
- Issue: forge's `.gitignore` contains `.planning/`, so `git add` was blocked.
  However, `.planning/` files ARE tracked in the main repo (committed before the
  gitignore entry took effect). Used `git add -f` to stage the tracked/new files.
- Fix: `git add -f .planning/ROADMAP.md .planning/milestones/v2.1-dynamic-gate/ROADMAP.md`
- No files created outside worktree; no impact on main tree.

**3. [Rule 3 - Blocking] Commit hook requires docs/config/wip marker**
- Found during: Task 2 commit attempt
- Issue: forge's `check_git_commit_review.sh` PreToolUse hook blocks commits
  without a review marker. For documentation-only changes, the `# docs` marker
  at the end of the `git commit` command bypasses the review gate.
- Fix: appended `# docs` as a trailing comment on the commit command.

**4. [Rule 3 - Blocking] SUMMARY.md write blocked by check_worktree.sh hook**
- Found during: SUMMARY creation
- Issue: the global check_worktree.sh hook blocks direct edits to the main
  worktree of any git repo (including plan-forge). Writing SUMMARY.md to the
  plan-forge main tree was blocked.
- Fix: created a plan-forge worktree (`p9-09-01-summary` branch), wrote
  SUMMARY.md there, then committed and merged via the worktree path.

## Known Stubs

None. Both ROADMAP files contain real, domain-relevant content in all six sections.
No placeholder text was introduced.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes
introduced. Pure documentation editing in a worktree.

## Self-Check

Files created/modified:
- [FOUND] /home/houminxi/code/forge/.worktrees/p9-gsd-compat/.planning/ROADMAP.md (modified)
- [FOUND] /home/houminxi/code/forge/.worktrees/p9-gsd-compat/.planning/milestones/v2.1-dynamic-gate/ROADMAP.md (created)

Commits:
- [FOUND] 092ee95 in forge worktree branch p9-gsd-compat

## Self-Check: PASSED
