# P5 FP Fixture: file-granularity T-row coverage and mode strings

T-rows reference `record.py` and `query.py` at file granularity rather
than listing each function individually.  The mode strings `off` and
`on_split_evidence_rich` appear as backtick values in T-rows but are
not APIs (no matching `def`).  The anchor function `emit_report` is
listed by name so that t_row_outputs is non-empty and the file-granularity
coverage logic is exercised.

## Module Designs

```python
def record_outcome(run_id: str, verdict: str) -> None:
    pass

def query_results(run_id: str) -> list:
    pass

def emit_report(data: dict) -> str:
    pass
```

## Implementation Tasks

| Task | Output |
|------|--------|
| T01  | `record.py` |
| T02  | `query.py` |
| T03  | `emit_report` |
| T04  | arbitration mode `off` or `on_split_evidence_rich` |
