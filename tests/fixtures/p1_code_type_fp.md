# P1 Code-Type FP Fixture

A code block defines ResultType as a return annotation.  A single backtick
mention in prose must not fire P1 because the type is defined in the block.

## Design

The loader returns a `ResultType` on success.

```python
def load() -> ResultType:
    ...
```

## Notes

No further prose reference is needed.
