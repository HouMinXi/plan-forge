## Overview

The lock release timing must be coordinated with the scheduler to avoid
priority inversion in the kernel path.

## Implementation

Adjusting lock release timing requires inserting a memory barrier before
the unlock call to ensure the store buffer is flushed first.

## Verification

Correct lock release timing can be confirmed by running the latency
profiler and observing that no inversion is recorded across 1000 samples.
