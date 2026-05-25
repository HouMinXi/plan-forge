# P2 TP Fixture: Function Return Optional Without Handling

A function that returns an optional type but whose return value is
never null-checked in the same block is a propagation hazard.

## Module Design

```python
def load(path: str) -> Config | None:
    if not os.path.exists(path):
        return None
    return _parse(path)
```

The caller does not guard against the None return; no null-check,
assert, or default-value pattern appears in this block.
