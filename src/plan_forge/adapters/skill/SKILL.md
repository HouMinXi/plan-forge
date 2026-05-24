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

## Host-Search Orchestration (G8 citation verification)

When running /plan-forge in skill mode, the host (Claude session) drives
a contradiction-aware search before handing evidence to the gate. This
closes the G8 hole that bare-CLI mode leaves open: bare CLI relies on
provider knowledge alone, which cannot detect temporal contradictions
(e.g. a dead author cited on a post-mortem publication). The hole closes
only in skill mode because the host can run real web searches.

### Workflow

1. Extract citations and plan hash:

   ```
   python -m plan_forge.adapters.skill.runner extract-citations \
     --plan-path <path>
   ```

   Output is JSON: {"plan_hash": "<sha256>", "citations": ["...", ...]}.
   Save plan_hash for step 4.

2. For EACH citation, run contradiction-aware searches. Parse the
   author(s) and year from the citation string, then run three SEPARATE
   search queries per citation:

   (a) Work existence: search for the title + author + year together.
       Goal: confirm the work exists as cited (correct title, author
       attribution, publication year).
       Example query: "Attention Is All You Need Vaswani 2017"

   (b) Author background: for each author, search for biographical
       information INCLUDING life and death dates.
       Example query: "Alan Turing biography born died"
       This is critical: a title-only search finds the book and MISSES
       the fact that the cited author died before the publication year.

   (c) Temporal consistency: cross-check author death year against the
       cited publication year; verify the venue or publisher existed at
       the cited year.
       Example query: "NeurIPS conference history founding year"
       If the author died in 1954 and the citation says 2010, the
       contradiction is visible only when (b) provides death dates and
       (c) confirms the venue timeline.

   Do NOT search the citation title only. A title-only search returns
   the work and confirms it exists, but it cannot surface the author
   lifespan contradiction that makes a citation fabricated. The three
   separate searches ensure the model SEES the conflicting facts.

3. Tier each search hit. Use a two-tier default:
   - T1_GOLD for primary/official sources (publisher pages, arxiv,
     university profiles, official biographies).
   - T2_SILVER for secondary sources (Wikipedia, news articles, blog
     posts, general reference sites).
   Fine-grained tier classification does not drive the verdict (the eval
   showed tier has no measurable effect on accuracy); keep it simple.

4. Build the evidence file. Construct a JSON dict with this shape:

   ```json
   {
     "plan_hash": "<sha256 from step 1>",
     "evidence": {
       "<citation string>": [
         {
           "tier": "T1_GOLD",
           "domain": "arxiv.org",
           "title": "Attention Is All You Need",
           "snippet": "Vaswani et al. 2017, Transformer...",
           "url": "https://arxiv.org/abs/1706.03762"
         }
       ],
       "<citation that found nothing>": [],
       "<citation where search errored>": {"search_failed": true}
     }
   }
   ```

   Write it to a tempfile (mkstemp). The plan_hash lets the analyze step
   detect if the plan changed after evidence was gathered.

5. Run analysis with the evidence file:

   ```
   python -m plan_forge.adapters.skill.runner analyze \
     --plan-path <path> --evidence-file <tmpfile>
   ```

   If plan_hash mismatches (plan was edited since step 1), the output
   includes a MEDIUM finding advising re-run. The run still proceeds.

6. Cleanup: unlink the tempfile in a try/finally block. Then proceed
   to arbitration (step 5-7 of the main workflow above).

### Notes

- The v1 evidence-mode prompt (g8_citation_resolvability_v1.txt) already
  tells providers: "Use ONLY the host-provided evidence below; do not
  search; do NOT populate the search_evidence field." No additional
  prompt changes are needed when host evidence is present.
- Production mimo uses its default configuration (thinking enabled).
  The eval showed thinking-on achieves 91.7% accuracy with evidence,
  higher than thinking-off. Do not disable thinking for evidence mode.
- Bare-CLI users (no host search) get the existing behavior: providers
  answer from training-corpus knowledge alone. The G8 contradiction
  hole is closed only in skill mode where the host drives real searches.
  This is a known, accepted limitation of bare-CLI usage.

## Requirements

- plan-forge must be installed: pip install -e .
- For capture to persist verdicts: PLAN_FORGE_CORPUS_URL must be set.
- To make /plan-forge invocable, symlink or copy this file to
  ~/.claude/skills/plan-forge/SKILL.md.
