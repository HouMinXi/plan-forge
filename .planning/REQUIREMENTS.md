# plan-forge v0.1.1 -- Requirements

## v1 Requirements

### G8 Citation Severity (GATE-01)

- [ ] **GATE-01**: G8.A.no_citation severity changed from BLOCKER to HIGH so plans
      with prose citations ("Nielsen (2022) showed...") are not blocked
- [ ] **GATE-02**: Existing G8 TP fixture still fires (anti-gutting verified)
- [ ] **GATE-03**: Empty External Voices section distinction: a truly empty section
      should remain BLOCKER; unparseable-but-present content becomes HIGH

### F2 Structural Noise (GATE-04)

- [ ] **GATE-04**: F2 no longer fires on capitalized n-grams that are plan section
      headings (e.g. "Implementation Tasks", "Success Criteria")
- [ ] **GATE-05**: F2 TP fixture still fires on genuine repeated factual assertions

### GSD Format Compatibility (GSD-01)

- [ ] **GSD-01**: Documented fix path: forge GSD templates updated to embed plan-forge
      canonical keywords in headings (e.g. "## Architecture & Reference Class")
- [ ] **GSD-02**: After template fix, running api.check on a forge GSD planning doc
      produces 0 G-gate no_section BLOCKERs (was 36)

## v2 Requirements (deferred)

- Prose citation parser extension (NLP-hard, deferred post v0.1.1)
- Section-alias system in plan-forge (fails 100 LOC/3 consumers rule)
- F8.B contradiction detection

## Out of Scope

- New gates -- v0.2
- Holdout corpus -- v0.1.x backlog
- pip publish / package rename -- separate track
- MCP server -- v0.2

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GATE-01 | Phase 8 | Pending |
| GATE-02 | Phase 8 | Pending |
| GATE-03 | Phase 8 | Pending |
| GATE-04 | Phase 8 | Pending |
| GATE-05 | Phase 8 | Pending |
| GSD-01 | Phase 9 | Pending |
| GSD-02 | Phase 9 | Pending |
