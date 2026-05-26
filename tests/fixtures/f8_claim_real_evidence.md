# Claim + Real Evidence (FP fixture -- should NOT fire)

## Overview

The check catches real bugs in production codebases.

## Tests

- `test_with_live_repo.py`: runs against a real codebase extracted
  from a production repository.
- `test_corpus_plans.md`: exercises actual plan documents from the
  project corpus.

## Risks

- Real-world corpus may include confidential data.
