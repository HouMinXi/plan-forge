# Claim Only Inside Code Block (FP fixture -- should NOT fire)

## Overview

This plan discusses parsing improvements.

```python
# catches real bugs -- this is just a comment
def check(parsed):
    pass
```

## Tests

- `test_stub.py`: uses a stub ParsedPlan with mock data.

## Risks

- None identified.
