# P2 Fail Fixture

This plan has a nullable declaration with no null-handling.

## Module Designs

### Cache Handler

```python
def fetch_cached(key: str) -> bytes | None:
    return _store.get(key)
```

The function above returns None when the key is not found, but
there is no null-check in the block.

### User Record

```python
class UserRecord:
    profile: dict | None

    def display(self) -> str:
        return str(self.profile)
```

Neither `profile` nor the return of `fetch_cached` have null-checks.
