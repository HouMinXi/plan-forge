# F7 Pass Fixture

This fixture contains only ASCII characters.
No em dash, no smart quotes, no Unicode arrows.

## Design

Use plain ASCII hyphens -- not em dashes.
Use straight quotes "like this" not curly ones.
Use ASCII arrows -> not Unicode arrows.

## Summary

Every character in this file has ord() <= 127.
F7 should emit no findings.
