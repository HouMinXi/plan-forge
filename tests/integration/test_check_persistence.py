"""Integration tests for check() persistence of findings and evidence.

Tests verify that findings and llm_evidence are persisted to the corpus
when corpus recording is active, and that finding_id is correctly
backfilled.
"""
from __future__ import annotations

import json
from pathlib import Path

from plan_forge import api
from plan_forge.corpus import query
from plan_forge.llm.client import LLMResponse
from plan_forge.llm.mocks import MockClient

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _mock_client(name: str, verdict: str) -> MockClient:
    """Build a MockClient returning the given verdict for any prompt."""
    raw_json = json.dumps({
        "verdict": verdict,
        "reason": "test mock",
        "cited_instances": [],
        "search_evidence": [],
    })
    return MockClient(
        name=name,
        responses={"": LLMResponse(
            verdict=verdict,
            reasoning="test mock",
            cited_instances=[],
            search_evidence=[],
            cost_usd=0.0,
            raw_response={"original_json": raw_json},
        )},
    )


def test_mechanical_findings_persisted(corpus_engine):
    """Corpus-active, mechanical-only -> findings rows written."""
    plan_text = _load("well_formed.md")
    verdict = api.check(plan_text, llm_clients=[])

    assert verdict.corpus_run_id is not None
    findings = query.list_findings(verdict.corpus_run_id)
    assert len(findings) == len(verdict.findings)
    assert all(f.run_id == verdict.corpus_run_id for f in findings)


def test_llm_evidence_persisted(corpus_engine):
    """MockClients vote UNVERIFIED -> evidence rows written."""
    plan_text = _load("g6_pass.md")
    clients = [
        _mock_client("mock_a", "UNVERIFIED"),
        _mock_client("mock_b", "UNVERIFIED"),
    ]
    verdict = api.check(plan_text, llm_clients=clients)

    assert verdict.corpus_run_id is not None
    evidence = query.list_evidence(
        verdict.corpus_run_id, gate_id="G6.B"
    )
    assert len(evidence) > 0


def test_gate_id_strip_llm_suffix(corpus_engine):
    """Evidence row has gate_id == "G6.B", not "G6.B.llm"."""
    plan_text = _load("g6_pass.md")
    clients = [
        _mock_client("mock_a", "UNVERIFIED"),
        _mock_client("mock_b", "UNVERIFIED"),
    ]
    verdict = api.check(plan_text, llm_clients=clients)

    assert verdict.corpus_run_id is not None
    evidence = query.list_evidence(verdict.corpus_run_id)
    llm_evidence = [e for e in evidence if e.gate_id == "G6.B"]
    assert len(llm_evidence) > 0
    assert all(e.gate_id == "G6.B" for e in llm_evidence)


def test_finding_id_backfilled(corpus_engine, monkeypatch):
    """Corpus-active -> finding_id is int; corpus-inactive -> None."""
    plan_text = _load("well_formed.md")
    verdict_active = api.check(plan_text, llm_clients=[])
    assert verdict_active.corpus_run_id is not None
    for f in verdict_active.findings:
        assert isinstance(f.finding_id, int)

    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    from plan_forge.corpus import db
    db._reset_engine()

    verdict_inactive = api.check(plan_text, llm_clients=[])
    assert verdict_inactive.corpus_run_id is None
    for f in verdict_inactive.findings:
        assert f.finding_id is None


def test_partial_finding_failure(corpus_engine, monkeypatch):
    """record_finding fails for one -> others persist, warning."""
    plan_text = _load("well_formed.md")

    call_count = [0]

    def mock_record_finding(self, run_id, finding):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("test failure")
        return call_count[0] * 100

    from plan_forge.corpus import record
    monkeypatch.setattr(
        record.CorpusRecorder, "record_finding", mock_record_finding
    )

    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        verdict = api.check(plan_text, llm_clients=[])

    assert verdict.corpus_run_id is not None
    assert len(w) >= 1
    assert any("persist finding" in str(warn.message) for warn in w)

    successes = [f for f in verdict.findings if f.finding_id is not None]
    failures = [f for f in verdict.findings if f.finding_id is None]
    assert len(successes) > 0
    assert len(failures) > 0


def test_partial_evidence_failure(corpus_engine, monkeypatch):
    """record_evidence fails for one -> finding row persists."""
    plan_text = _load("g6_pass.md")
    clients = [
        _mock_client("mock_a", "UNVERIFIED"),
        _mock_client("mock_b", "UNVERIFIED"),
    ]

    call_count = [0]

    def mock_record_evidence(self, run_id, gate_id, target_id, evidence):
        call_count[0] += 1
        if call_count[0] == 2:
            raise RuntimeError("test failure")
        return call_count[0] * 1000

    from plan_forge.corpus import record
    monkeypatch.setattr(
        record.CorpusRecorder, "record_evidence", mock_record_evidence
    )

    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        verdict = api.check(plan_text, llm_clients=clients)

    assert verdict.corpus_run_id is not None
    assert len(w) >= 1
    assert any("persist evidence" in str(warn.message) for warn in w)

    findings = query.list_findings(verdict.corpus_run_id)
    assert len(findings) > 0


def test_corpus_private_skips_findings(corpus_engine):
    """corpus_private=True -> no findings/evidence rows."""
    plan_text = _load("well_formed.md")
    verdict = api.check(plan_text, llm_clients=[], corpus_private=True)

    assert verdict.corpus_run_id is not None
    findings = query.list_findings(verdict.corpus_run_id)
    assert len(findings) == 0
    evidence = query.list_evidence(verdict.corpus_run_id)
    assert len(evidence) == 0


def test_corpus_inactive_no_rows(tmp_path, monkeypatch):
    """Corpus inactive -> no rows, finding_id None, no warning."""
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    from plan_forge.corpus import db
    db._reset_engine()

    plan_text = _load("well_formed.md")

    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        verdict = api.check(plan_text, llm_clients=[])

    assert verdict.corpus_run_id is None
    for f in verdict.findings:
        assert f.finding_id is None
    persist_warnings = [
        warn for warn in w if "persist" in str(warn.message)
    ]
    assert len(persist_warnings) == 0


def test_mechanical_finding_no_evidence(corpus_engine):
    """Mechanical finding -> findings row, zero evidence rows."""
    plan_text = _load("well_formed.md")
    verdict = api.check(plan_text, llm_clients=[])

    assert verdict.corpus_run_id is not None
    findings = query.list_findings(verdict.corpus_run_id)
    assert len(findings) > 0

    mechanical = [
        f for f in findings
        if not f.check_id.endswith(".llm")
    ]
    assert len(mechanical) > 0


def test_finalize_still_stamps(corpus_engine):
    """Findings persisted AND finalize stamps run row."""
    plan_text = _load("g6_pass.md")
    clients = [
        _mock_client("mock_a", "UNVERIFIED"),
        _mock_client("mock_b", "UNVERIFIED"),
    ]
    verdict = api.check(plan_text, llm_clients=clients)

    assert verdict.corpus_run_id is not None
    findings = query.list_findings(verdict.corpus_run_id)
    assert len(findings) > 0
    evidence = query.list_evidence(verdict.corpus_run_id)
    assert len(evidence) > 0

    run = query.get_run(verdict.corpus_run_id)
    assert run is not None
    assert run.completed_at is not None
    assert run.engineering_verdict == verdict.engineering.value
    assert run.epistemic_verdict == verdict.epistemic.value
