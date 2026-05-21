"""Tests for check and scaffold CLI handlers (Phase 2)."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from plan_forge.adapters.cli.main import main

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
WELL_FORMED = FIXTURES / "well_formed.md"
VISION_PLAN = FIXTURES / "vision_plan.md"


class TestCheckCommand:
    """Verify check subcommand exit codes and output."""

    def test_check_pass_exit0(self, capsys: pytest.CaptureFixture[str]):
        code = main(["check", str(WELL_FORMED), "--mechanical-only"])
        assert code == 0
        out = capsys.readouterr().out
        assert "Engineering: PASS" in out

    def test_check_fail_exit1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        # A plan with a BLOCKER-level finding (F1: orphan SC reference).
        plan = tmp_path / "bad.md"
        plan.write_text(
            "# Bad Plan\n\n"
            "## Success Criteria\n\n"
            "| SC | Criterion | Fail Condition |\n"
            "|----|-----------|----------------|\n"
            "| SC-1 | Works | FAILS if broken |\n\n"
            "## Test Plan\n\n"
            "- test_a: covers SC-1; does stuff\n"
            "- test_b: covers SC-99; ghost ref\n\n"
            "## Overview\n\nSome overview.\n",
            encoding="utf-8",
        )
        code = main(["check", str(plan), "--mechanical-only"])
        assert code == 1
        out = capsys.readouterr().out
        assert "FAIL" in out

    def test_check_vision_exit3(
        self, tmp_path: Path, monkeypatch,
        capsys: pytest.CaptureFixture[str],
    ):
        # SUBSPEC interpretation: exit 3 requires engineering=PASS +
        # epistemic=VISION. With api.check(), G1/G7 BLOCKERs fail
        # engineering too (FAIL>VISION in exit mapping). Monkeypatch
        # api.check to return a PASS+VISION verdict directly, proving
        # the exit-code mapping handles code 3 correctly.
        from plan_forge.verdict import Verdict, EngineeringVerdict, EpistemicVerdict

        plan = tmp_path / "vision.md"
        plan.write_text("# Vision\n", encoding="utf-8")

        def _vision_verdict(*_a, **_kw):
            return Verdict(
                engineering=EngineeringVerdict.PASS,
                epistemic=EpistemicVerdict.VISION,
            )

        monkeypatch.setattr("plan_forge.adapters.cli.main.api.check", _vision_verdict)
        code = main(["check", str(plan), "--mechanical-only"])
        assert code == 3
        out = capsys.readouterr().out
        assert "VISION" in out

    def test_check_vision_plan_fail_beats_vision(
        self, capsys: pytest.CaptureFixture[str],
    ):
        # vision_plan.md has G1/G7 absent -> engineering=FAIL +
        # epistemic=VISION. Per 1.2, FAIL takes precedence -> exit 1.
        code = main(["check", str(VISION_PLAN), "--mechanical-only"])
        assert code == 1
        out = capsys.readouterr().out
        assert "Engineering: FAIL" in out
        assert "Epistemic: VISION" in out

    def test_check_missing_file_exit4(self, capsys: pytest.CaptureFixture[str]):
        code = main(["check", "/nonexistent/plan.md", "--mechanical-only"])
        assert code == 4
        err = capsys.readouterr().err
        assert "error:" in err

    def test_check_dir_as_file_exit4(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        code = main(["check", str(tmp_path), "--mechanical-only"])
        assert code == 4
        err = capsys.readouterr().err
        assert "error:" in err

    def test_check_preamble_passes(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        plan = tmp_path / "plan.md"
        shutil.copy2(WELL_FORMED, plan)
        preamble = tmp_path / "preamble.md"
        preamble.write_text("Build the thing.\n", encoding="utf-8")
        code = main([
            "check", str(plan), "--mechanical-only",
            "--preamble", str(preamble),
        ])
        # Preamble is accepted; exit per verdict (pass or vision, not 4).
        assert code in (0, 1, 3)

    def test_check_preamble_missing_exit4(
        self, capsys: pytest.CaptureFixture[str],
    ):
        code = main([
            "check", str(WELL_FORMED), "--mechanical-only",
            "--preamble", "/nonexistent/preamble.md",
        ])
        assert code == 4
        err = capsys.readouterr().err
        assert "error:" in err


class TestScaffoldCommand:
    """Verify scaffold subcommand exit codes and output."""

    def test_scaffold_writes_exit0(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        code = main(["scaffold", "my-plan", "--output-dir", str(tmp_path)])
        assert code == 0
        out = capsys.readouterr().out.strip()
        written = Path(out)
        assert written.exists()
        assert written.name == "my-plan.md"

    def test_scaffold_default_output_dir(
        self, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str],
    ):
        monkeypatch.chdir(tmp_path)
        code = main(["scaffold", "default-plan"])
        assert code == 0
        out = capsys.readouterr().out.strip()
        assert Path(out).exists()
        assert (tmp_path / "default-plan.md").exists()

    def test_scaffold_existing_exit4(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        main(["scaffold", "dup", "--output-dir", str(tmp_path)])
        code = main(["scaffold", "dup", "--output-dir", str(tmp_path)])
        assert code == 4
        err = capsys.readouterr().err
        assert "error:" in err

    def test_scaffold_unsafe_name_exit4(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        code = main(["scaffold", "../evil", "--output-dir", str(tmp_path)])
        assert code == 4
        err = capsys.readouterr().err
        assert "error:" in err
