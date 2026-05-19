# F4 Fail Fixture

This plan uses an imprecise temporal phrase that should trigger F4.

## Design

The cache is flushed after the function is complete.
We must process the queue before the handler is done.

## Summary

The phrases "after the function is complete" and "before the handler
is done" lack precise anchors.  They do not use __exit__, a dunder,
or a capitalized specific symbol.  F4 should emit findings for both.
