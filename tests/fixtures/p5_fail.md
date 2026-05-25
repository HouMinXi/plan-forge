# P5 Fail Fixture

Module Designs and T-row outputs are asymmetric in both directions.
compute_hash is in Module Designs but not listed in any T-row.
serialize_record is listed in a T-row and defined in Requirements
but has no Module Designs entry.

## Requirements

The implementation requires a serialization helper:

```python
def serialize_record(data: dict) -> str:
    pass
```

## Module Designs

```python
def parse_document(text: str) -> dict:
    pass

def compute_hash(data: bytes) -> str:
    pass
```

## Implementation Tasks

| Task | Description | Output |
|------|-------------|--------|
| T01 | Implement parser | `parse_document` |
| T02 | Implement serializer | `serialize_record` |
