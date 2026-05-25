# P5 TP Fixture: orphaned Module Designs API

An API defined in Module Designs but absent from Implementation Tasks.
P5.module_design_orphan must still fire after the file-granularity fix.

## Module Designs

```python
def frobnicate(x: int) -> str:
    pass

def covered_api(data: dict) -> None:
    pass
```

## Implementation Tasks

| Task | Output | Notes |
|------|--------|-------|
| T01  | `covered_api` | this one is covered |
| T02  | `unrelated.py` | handles something else |
