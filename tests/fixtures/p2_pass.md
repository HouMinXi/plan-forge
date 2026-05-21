# P2 Pass Fixture

Every nullable declaration in this plan has explicit null-handling.

## Module Designs

### Validator

```python
def validate(data: Optional[dict]) -> bool:
    if data is None:
        raise ValueError("data required")
    return len(data) > 0
```

### Formatter

```python
def format_label(label: str | None) -> str:
    display = label or "unknown"
    return display
```

### Checker

```python
def check_result(result: dict | None) -> bool:
    assert result is not None
    return len(result) > 0
```
