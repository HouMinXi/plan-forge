# F4 Pass Fixture

Temporal phrases use precise anchors so no F4 findings are expected.

## Design

The connection is released after __exit__ is called by the context
manager.  Resources are cleaned up after __exit__ completes.

The callback runs after CallerAssignment is stored in the registry.

## Code

```python
def __exit__(self, exc_type, exc_val, exc_tb):
    # after return from this method the resource is gone
    self.close()
    return False
```

## Summary

All temporal phrases either use dunders or capitalized precise symbols.
No fuzzy lifecycle verbs appear in imprecise contexts.
