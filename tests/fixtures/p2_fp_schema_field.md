# P2 FP Fixture: Schema Field Declarations

Field declarations in a schema or model block describe data shape.
They are not null-propagation hazards even when typed as optional.

## Data Model

```python
class ArbitrationRecord(Base):
    human_verdict: str | None
    denial_reason: str | None
    corpus_run_id: int | None
    arbitration_resolution: str | None
    finding_id: str | None
```

No null-handling is required for the fields above; they are column
definitions, not function return values that callers must guard.
