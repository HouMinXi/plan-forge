# plan-forge

An epistemological gate for plan documents authored by humans working with AI assistance.

Plan-forge enforces falsifiability discipline on plans BEFORE they get implemented.
Where a code reviewer asks "is this code correct?", plan-forge asks "is this a plan
or a vision dressed up as a plan?"

Read `MANIFESTO.md` before contributing or modifying any check.

## What it checks

**Mechanical gates (F1-F9)** -- deterministic, run without LLM:
- F1 SC traceability: every success criterion is traceable to a requirement
- F2 Null propagation: optional returns have documented handling
- F3 Cross-plan invariants: cross-plan references are audited
- F4 Temporal consistency: dates and sequencing are internally consistent
- F5 Interface symmetry: Module Designs match Implementation Tasks
- F6 Numeric consistency: quantitative claims are internally consistent
- F7 ASCII hygiene: no invisible non-ASCII characters
- F8 Plan consistency: capability claims are backed by real evidence, not mocks
- F9 Plan length: flags plans over 500 lines as too long to review reliably

**Epistemic gates (G1-G10)** -- LLM-assisted:
- G1-G3: section completeness, risk taxonomy, measurability
- G4: probability calibration (hedged claims must be quantified)
- G5-G10: scope challenge, source diversity, feasibility, consistency, citation resolvability

**PBR gates (P1, P2, P5, P6)** -- perspective-based reading checks

## Install

```bash
pip install plan-forge        # or: uv add plan-forge
```

Requires Python 3.13+. Database migrations (SQLite by default):

```bash
alembic upgrade head
```

## Quick start

```bash
# Check a plan (mechanical gates only, no LLM needed)
plan-forge check --plan-path my-plan.md

# Check with LLM providers
export PLAN_FORGE_DEEPSEEK_API_KEY=sk-...
plan-forge check --plan-path my-plan.md

# Extract citations for host-search evidence injection
plan-forge extract-citations --plan-path my-plan.md

# Record an outcome against a plan run
plan-forge record-outcome <run-id> --type predicted_manifested --recorder me

# Check abandonment (SC-19 self-falsification clause)
plan-forge abandonment-check
```

## Development setup

Prerequisites: Python 3.13+, [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/HouMinXi/plan-forge
cd plan-forge
uv venv --python 3.13
uv pip install -e .[dev] --python .venv/bin/python
uv run alembic upgrade head
uv run pytest tests/ -q
```

### Optional: Postgres backend

```bash
docker compose up -d
uv pip install -e .[dev,postgres] --python .venv/bin/python
export PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge
uv run alembic upgrade head
```

## LLM providers

Configure via environment variables:

```bash
export PLAN_FORGE_DEEPSEEK_API_KEY=sk-...
export PLAN_FORGE_MIMO_API_KEY=...
export PLAN_FORGE_KIMI_API_KEY=...
export PLAN_FORGE_ANTHROPIC_API_KEY=sk-ant-...
```

Mechanical gates (F1-F9) run with no providers configured. Epistemic gates (G-series)
require at least one provider. The tool degrades gracefully when providers are absent.

## Status

v0.1.0 -- first tagged release. Self-dogfood: `api.check` on the project's own master
plan returns engineering=PASS, epistemic=PASS with no HIGH or BLOCKER findings.

Known limitations documented in `.planning/T34-SC3-AUDIT.md` and `LESSONS-RETRO.md`.
v0.1.x work: holdout corpus, F8.B contradiction detection, F3 per-mention dedup,
format generalization beyond plan-forge's own section-name conventions.

## License

Apache License 2.0 -- see [LICENSE](LICENSE).
