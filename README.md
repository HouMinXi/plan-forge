# plan-forge

## Development setup

Prerequisites: Python 3.13+, uv.

1. Install plan-forge in editable mode:
   ```
   uv venv --python 3.13
   uv pip install -e .[dev] --python .venv/bin/python
   ```
2. Apply database migrations (creates SQLite corpus DB at
   `~/.local/share/plan-forge/corpus.db`):
   ```
   .venv/bin/alembic upgrade head
   ```
3. Run tests:
   ```
   .venv/bin/pytest tests/ -q
   ```

### Optional: switch to Postgres

For multi-user / production use, start the bundled Postgres
service and point plan-forge at it:

```
docker compose up -d
uv pip install -e .[dev,postgres] --python .venv/bin/python
export PLAN_FORGE_CORPUS_URL=postgresql+psycopg://plan_forge:dev@localhost:5432/plan_forge
.venv/bin/alembic upgrade head
```

The same migrations and ORM models work on both backends.

An epistemological gate for plans, drafts, and proposals authored by humans
working with AI assistance.

## What it is

Plan-forge enforces falsifiability discipline on plan documents BEFORE they get
implemented. Where forge-code blocks AI-generated code garbage at the
plan-to-code transition, plan-forge blocks AI-generated plan garbage at the
idea-to-plan transition.

## What it is NOT

Not a markdown linter. Not a style checker. Not a spelling tool.

A linter asks "is this text well-formed?" Plan-forge asks "is this a plan or a
vision dressed up as a plan?"

## Status

v0.1 in early planning. See `.planning/plan-forge-v0.1-PLAN.md` and
`MANIFESTO.md`.

## Philosophy

Read `MANIFESTO.md` FIRST before contributing or modifying any check.

## License

TBD.
