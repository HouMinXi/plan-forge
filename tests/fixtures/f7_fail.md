# F7 Fail Fixture

This fixture intentionally contains non-ASCII characters.

## Design

The connection—managed by the pool—must be closed properly.
Use “smart quotes” around identifiers.
Data flows from parser → checker.

## Summary

Three non-ASCII characters appear above:
- U+2014 em dash in the Design section.
- U+201C/U+201D smart double quotes around smart quotes.
- U+2192 right arrow between parser and checker.
F7 should emit findings for each.
