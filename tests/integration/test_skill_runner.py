"""Integration tests for plan_forge.adapters.skill.runner (T28).

Each test calls runner.main(argv) in-process and captures stdout via
capsys.  Capture tests use corpus_engine fixture for a real DB.
Monkeypatch api.check for deterministic split candidates where needed.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from plan_forge.adapters.skill import runner
from plan_forge.corpus.models import Arbitration
from plan_forge.verdict import (
    EngineeringVerdict,
    EpistemicVerdict,
    Finding,
    LLMEvidence,
    Severity,
    Verdict,
)

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
_SKILL_MD = (
    Path(__file__).resolve().parent.parent.parent
    / "src"
    / "plan_forge"
    / "adapters"
    / "skill"
    / "SKILL.md"
)


def _plan_path(name: str = "f1_pass.md") -> str:
    return str(_FIXTURES / name)


def _parsed(out: str) -> dict:
    return json.loads(out)


def _fake_verdict_split() -> Verdict:
    """Build a Verdict with one split+evidence-rich finding (G6.A)."""
    ev_a = LLMEvidence(
        provider="a",
        model="m",
        verdict="FAIL",
        reasoning="r",
        prompt_version="v1",
        run_id=None,
        cited_instances=[{"snippet": "s", "issue": "i"}],
    )
    ev_b = LLMEvidence(
        provider="b",
        model="m",
        verdict="PASS",
        reasoning="r",
        prompt_version="v1",
        run_id=None,
        cited_instances=[{"snippet": "s", "issue": "i"}],
    )
    f = Finding(
        check_id="G6.A",
        severity=Severity.HIGH,
        location="plan.md:1",
        message="msg",
        llm_evidence=[ev_a, ev_b],
    )
    return Verdict(
        engineering=EngineeringVerdict.FAIL,
        epistemic=EpistemicVerdict.FAIL,
        findings=[f],
    )


def _row(engine, arb_id: int) -> Arbitration:
    with Session(engine) as s:
        row = s.get(Arbitration, arb_id)
        assert row is not None
        s.expunge(row)
    return row


def _write_session(run_id: int, candidates: list[dict]) -> str:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    )
    json.dump({"run_id": run_id, "candidates": candidates}, tmp)
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# 1. analyze mechanical-only plan -> candidates==[], exit 0
# ---------------------------------------------------------------------------

def test_analyze_mechanical_only_no_candidates(capsys, monkeypatch):
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    rc = runner.main([
        "analyze",
        "--plan-path", _plan_path("f1_pass.md"),
        "--mechanical-only",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert out["arbitration_candidates"] == []
    assert out["session_file"] is None


# ---------------------------------------------------------------------------
# 2. analyze with corpus active -> corpus_active true, run_id is int
# ---------------------------------------------------------------------------

def test_analyze_corpus_active_run_id_is_int(
    capsys, corpus_engine, monkeypatch
):
    rc = runner.main([
        "analyze",
        "--plan-path", _plan_path("f1_pass.md"),
        "--mechanical-only",
        "--arbitration-mode", "off",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert out["corpus_active"] is True
    assert isinstance(out["run_id"], int)


# ---------------------------------------------------------------------------
# 3. analyze with corpus INACTIVE -> corpus_active false, run_id null,
#    session_file null, exit 0
# ---------------------------------------------------------------------------

def test_analyze_corpus_inactive(capsys, monkeypatch):
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    rc = runner.main([
        "analyze",
        "--plan-path", _plan_path("f1_pass.md"),
        "--mechanical-only",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert out["corpus_active"] is False
    assert out["run_id"] is None
    assert out["session_file"] is None


# ---------------------------------------------------------------------------
# 4. analyze with monkeypatched check() returning split+evidence-rich
#    finding -> candidates has 1 entry, bundle_text has "# Arbitration:",
#    session_file written
# ---------------------------------------------------------------------------

def test_analyze_split_finding_candidate(
    capsys, corpus_engine, monkeypatch
):
    fake = _fake_verdict_split()
    fake = Verdict(
        engineering=fake.engineering,
        epistemic=fake.epistemic,
        findings=fake.findings,
        corpus_run_id=1,
    )

    def _mock_check(plan_text, **kwargs):
        return fake

    monkeypatch.setattr("plan_forge.api.check", _mock_check)

    rc = runner.main([
        "analyze",
        "--plan-path", _plan_path("f1_pass.md"),
        "--arbitration-mode", "on_split_evidence_rich",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert len(out["arbitration_candidates"]) == 1
    c = out["arbitration_candidates"][0]
    assert "# Arbitration:" in c["bundle_text"]
    assert out["session_file"] is not None
    assert os.path.isfile(out["session_file"])
    os.unlink(out["session_file"])


# ---------------------------------------------------------------------------
# 5. analyze returns exit 0 even when engineering==FAIL
# ---------------------------------------------------------------------------

def test_analyze_engineering_fail_exits_0(capsys, monkeypatch):
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    rc = runner.main([
        "analyze",
        "--plan-path", _plan_path("f1_fail.md"),
        "--mechanical-only",
        "--arbitration-mode", "off",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert out["engineering"] == "FAIL"


# ---------------------------------------------------------------------------
# 6. capture valid session, index 0, "unverified" -> arbitration_id
#    returned, DB row has overrode_llm=True
# ---------------------------------------------------------------------------

def test_capture_unverified_overrode_llm_true(
    capsys, corpus_engine
):
    from plan_forge.corpus.record import CorpusRecorder

    class _FakePlan:
        raw_text = "# Plan\nsome text"

    rec = CorpusRecorder()
    run_id = rec.start_run(_FakePlan(), None, "0.0.0", "off", 0.0)

    bundle_text = "## Finding\nsome evidence"
    candidates = [
        {
            "index": 0,
            "check_id": "G6.A",
            "location": "plan.md:1",
            "bundle_text": bundle_text,
        }
    ]
    sf = _write_session(run_id, candidates)

    rc = runner.main([
        "capture",
        "--session-file", sf,
        "--index", "0",
        "--verdict", "unverified",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert "arbitration_id" in out
    arb_id = out["arbitration_id"]
    row = _row(corpus_engine, arb_id)
    assert row.overrode_llm is True
    os.unlink(sf)


# ---------------------------------------------------------------------------
# 7. capture "verified" -> overrode_llm False; "deferred" -> None
# ---------------------------------------------------------------------------

def test_capture_verified_and_deferred(capsys, corpus_engine):
    from plan_forge.corpus.record import CorpusRecorder

    class _FakePlan:
        raw_text = "# Plan\nsome text"

    rec = CorpusRecorder()
    run_id = rec.start_run(_FakePlan(), None, "0.0.0", "off", 0.0)

    bundle_text = "## Finding\nevidence"
    candidates = [
        {
            "index": 0,
            "check_id": "G6.A",
            "location": "plan.md:1",
            "bundle_text": bundle_text,
        },
        {
            "index": 1,
            "check_id": "G6.A",
            "location": "plan.md:2",
            "bundle_text": bundle_text,
        },
    ]
    sf = _write_session(run_id, candidates)

    rc_v = runner.main([
        "capture", "--session-file", sf,
        "--index", "0", "--verdict", "verified",
    ])
    out_v = _parsed(capsys.readouterr().out)
    assert rc_v == 0
    row_v = _row(corpus_engine, out_v["arbitration_id"])
    assert row_v.overrode_llm is False

    rc_d = runner.main([
        "capture", "--session-file", sf,
        "--index", "1", "--verdict", "deferred",
    ])
    out_d = _parsed(capsys.readouterr().out)
    assert rc_d == 0
    row_d = _row(corpus_engine, out_d["arbitration_id"])
    assert row_d.overrode_llm is None

    os.unlink(sf)


# ---------------------------------------------------------------------------
# 8. capture out-of-range index -> JSON error + exit 1; no DB row written
# ---------------------------------------------------------------------------

def test_capture_out_of_range_index(capsys, corpus_engine):
    from plan_forge.corpus.record import CorpusRecorder
    from sqlalchemy import text

    class _FakePlan:
        raw_text = "# Plan\nsome text"

    rec = CorpusRecorder()
    run_id = rec.start_run(_FakePlan(), None, "0.0.0", "off", 0.0)

    candidates = [
        {
            "index": 0,
            "check_id": "G6.A",
            "location": "plan.md:1",
            "bundle_text": "some bundle",
        }
    ]
    sf = _write_session(run_id, candidates)

    with Session(corpus_engine) as s:
        before = s.execute(
            text("SELECT COUNT(*) FROM arbitrations")
        ).scalar_one()

    rc = runner.main([
        "capture", "--session-file", sf,
        "--index", "5", "--verdict", "verified",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 1
    assert "error" in out
    assert "out of range" in out["error"]

    with Session(corpus_engine) as s:
        after = s.execute(
            text("SELECT COUNT(*) FROM arbitrations")
        ).scalar_one()
    assert after == before
    os.unlink(sf)


# ---------------------------------------------------------------------------
# 9. capture with corpus inactive -> JSON error "corpus inactive" + exit 1
# ---------------------------------------------------------------------------

def test_capture_corpus_inactive(capsys, monkeypatch, tmp_path):
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    sf = str(tmp_path / "session.json")
    sf_path = Path(sf)
    sf_path.write_text(
        json.dumps({"run_id": 1, "candidates": []}),
        encoding="utf-8",
    )
    rc = runner.main([
        "capture", "--session-file", sf,
        "--index", "0", "--verdict", "verified",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 1
    assert "corpus inactive" in out["error"]


# ---------------------------------------------------------------------------
# 10. invalid --arbitration-mode (analyze) -> argparse rejects, exit nonzero
# ---------------------------------------------------------------------------

def test_analyze_invalid_arbitration_mode(monkeypatch):
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    with pytest.raises(SystemExit) as exc_info:
        runner.main([
            "analyze",
            "--plan-path", _plan_path("f1_pass.md"),
            "--arbitration-mode", "bogus_mode",
        ])
    assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# 11. analyze on missing plan file -> JSON error + exit 1
# ---------------------------------------------------------------------------

def test_analyze_missing_plan_file(capsys, monkeypatch):
    monkeypatch.delenv("PLAN_FORGE_CORPUS_URL", raising=False)
    rc = runner.main([
        "analyze",
        "--plan-path", "/nonexistent/path/plan.md",
        "--mechanical-only",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 1
    assert "error" in out


# ---------------------------------------------------------------------------
# 12. SKILL.md has valid YAML frontmatter; name=="plan-forge"; ASCII only
# ---------------------------------------------------------------------------

def test_skill_md_frontmatter_and_ascii():
    content = _SKILL_MD.read_text(encoding="utf-8")
    # Must be pure ASCII
    for i, ch in enumerate(content):
        assert ord(ch) < 128, (
            f"non-ASCII char U+{ord(ch):04X} at byte {i}"
        )
    # Extract YAML frontmatter between --- delimiters
    assert content.startswith("---\n"), "SKILL.md must start with ---"
    end = content.index("\n---\n", 4)
    fm_text = content[4:end]
    # Parse key: value pairs manually (no pyyaml dependency)
    fm: dict[str, str] = {}
    current_key: str | None = None
    for line in fm_text.splitlines():
        if ":" in line and not line.startswith(" "):
            k, _, v = line.partition(":")
            current_key = k.strip()
            fm[current_key] = v.strip().strip('"')
        elif current_key is not None and line.startswith(" "):
            fm[current_key] = (
                fm[current_key] + " " + line.strip().strip('"')
            ).strip()
    assert fm.get("name") == "plan-forge"
    assert fm.get("description", "").strip() != ""


def test_analyze_includes_finding_id(capsys, corpus_engine, monkeypatch):
    """Corpus-active check() with finding_id -> candidate includes it."""
    fake = _fake_verdict_split()
    fake.findings[0].finding_id = 42
    fake = Verdict(
        engineering=fake.engineering,
        epistemic=fake.epistemic,
        findings=fake.findings,
        corpus_run_id=1,
    )

    def _mock_check(plan_text, **kwargs):
        return fake

    monkeypatch.setattr("plan_forge.api.check", _mock_check)

    rc = runner.main([
        "analyze",
        "--plan-path", _plan_path("f1_pass.md"),
        "--arbitration-mode", "on_split_evidence_rich",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    assert len(out["arbitration_candidates"]) == 1
    c = out["arbitration_candidates"][0]
    assert c["finding_id"] == 42
    if out["session_file"]:
        os.unlink(out["session_file"])


def test_capture_with_finding_id(capsys, corpus_engine):
    """Candidate with finding_id -> arbitration row links it."""
    from plan_forge.corpus.record import CorpusRecorder
    from plan_forge.verdict import Finding, Severity

    class _FakePlan:
        raw_text = "# Plan\nsome text"

    rec = CorpusRecorder()
    run_id = rec.start_run(_FakePlan(), None, "0.0.0", "off", 0.0)

    finding = Finding(
        check_id="G6.A",
        severity=Severity.HIGH,
        location="plan.md:1",
        message="test finding",
    )
    real_finding_id = rec.record_finding(run_id, finding)

    bundle_text = "## Finding\nsome evidence"
    candidates = [
        {
            "index": 0,
            "check_id": "G6.A",
            "location": "plan.md:1",
            "bundle_text": bundle_text,
            "finding_id": real_finding_id,
        }
    ]
    sf = _write_session(run_id, candidates)

    rc = runner.main([
        "capture",
        "--session-file", sf,
        "--index", "0",
        "--verdict", "verified",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    arb_id = out["arbitration_id"]
    row = _row(corpus_engine, arb_id)
    assert row.finding_id == real_finding_id
    os.unlink(sf)


def test_capture_without_finding_id(capsys, corpus_engine):
    """Candidate missing finding_id -> arbitration row None."""
    from plan_forge.corpus.record import CorpusRecorder

    class _FakePlan:
        raw_text = "# Plan\nsome text"

    rec = CorpusRecorder()
    run_id = rec.start_run(_FakePlan(), None, "0.0.0", "off", 0.0)

    bundle_text = "## Finding\nsome evidence"
    candidates = [
        {
            "index": 0,
            "check_id": "G6.A",
            "location": "plan.md:1",
            "bundle_text": bundle_text,
        }
    ]
    sf = _write_session(run_id, candidates)

    rc = runner.main([
        "capture",
        "--session-file", sf,
        "--index", "0",
        "--verdict", "verified",
    ])
    out = _parsed(capsys.readouterr().out)
    assert rc == 0
    arb_id = out["arbitration_id"]
    row = _row(corpus_engine, arb_id)
    assert row.finding_id is None
    os.unlink(sf)
