"""Tests for audit-retroactive CLI handler."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from plan_forge.adapters.cli.main import main

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
WELL_FORMED = FIXTURES / "well_formed.md"
VISION_PLAN = FIXTURES / "vision_plan.md"


def _populate_dir(target: Path, sources: dict[str, Path]) -> None:
    """Copy fixture files into target under given filenames."""
    for name, src in sources.items():
        shutil.copy2(src, target / name)


class TestAuditRetroactive:
    """Verify audit-retroactive subcommand behaviour."""

    def test_audit_all_pass_exit0(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        _populate_dir(tmp_path, {
            "alpha.md": WELL_FORMED,
            "beta.md": WELL_FORMED,
        })
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        assert code == 0
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        # 2 per-file lines + 1 totals line
        assert len(lines) == 3
        assert "2 plans: 2 pass, 0 fail, 0 vision, 0 error" in lines[-1]

    def test_audit_one_fail_exit1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        _populate_dir(tmp_path, {"good.md": WELL_FORMED})
        bad = tmp_path / "bad.md"
        bad.write_text(
            "# Bad\n\n"
            "## Success Criteria\n\n"
            "| SC | Criterion | Fail Condition |\n"
            "|----|-----------|----------------|\n"
            "| SC-1 | Works | FAILS if broken |\n\n"
            "## Test Plan\n\n"
            "- test_a: covers SC-1; does stuff\n"
            "- test_b: covers SC-99; ghost ref\n\n"
            "## Overview\n\nOverview.\n",
            encoding="utf-8",
        )
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        assert code == 1
        out = capsys.readouterr().out
        totals = out.strip().splitlines()[-1]
        assert "2 plans:" in totals
        assert "1 fail" in totals

    def test_audit_all_vision_exit3(
        self, tmp_path: Path, monkeypatch,
        capsys: pytest.CaptureFixture[str],
    ):
        # SUBSPEC interpretation: exit 3 requires engineering=PASS +
        # epistemic=VISION for every file. Since api.check() with
        # vision_plan.md produces engineering=FAIL (G1/G7 BLOCKERs),
        # the real exit would be 1. Monkeypatch to produce the exact
        # verdict needed for pure-VISION rollup.
        from plan_forge.verdict import (
            Verdict, EngineeringVerdict, EpistemicVerdict,
        )

        _populate_dir(tmp_path, {
            "vis_a.md": VISION_PLAN,
            "vis_b.md": VISION_PLAN,
        })

        def _vision(*_a, **_kw):
            return Verdict(
                engineering=EngineeringVerdict.PASS,
                epistemic=EpistemicVerdict.VISION,
            )

        monkeypatch.setattr("plan_forge.adapters.cli.main.api.check", _vision)
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        assert code == 3
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        assert "2 plans: 0 pass, 0 fail, 2 vision, 0 error" in lines[-1]

    def test_audit_empty_dir_exit0(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        code = main(["audit-retroactive", str(tmp_path), "--mechanical-only"])
        assert code == 0
        out = capsys.readouterr().out
        assert "no plans found" in out

    def test_audit_missing_dir_exit4(
        self, capsys: pytest.CaptureFixture[str],
    ):
        code = main(["audit-retroactive", "/nonexistent/dir", "--mechanical-only"])
        assert code == 4
        err = capsys.readouterr().err
        assert "error:" in err

    def test_audit_ignores_non_md(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        _populate_dir(tmp_path, {"plan.md": WELL_FORMED})
        (tmp_path / "notes.txt").write_text("not a plan", encoding="utf-8")
        (tmp_path / "subdir").mkdir()
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        assert code == 0
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        # Only the .md file + totals
        assert len(lines) == 2
        assert "1 plans:" in lines[-1]

    def test_audit_sorted_order(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        _populate_dir(tmp_path, {
            "charlie.md": WELL_FORMED,
            "alpha.md": WELL_FORMED,
            "bravo.md": WELL_FORMED,
        })
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        assert code == 0
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        filenames = [line.split(":")[0] for line in lines[:-1]]
        assert filenames == ["alpha.md", "bravo.md", "charlie.md"]

    def test_audit_per_file_error_continues(
        self, tmp_path: Path, monkeypatch,
        capsys: pytest.CaptureFixture[str],
    ):
        # Use a unique sentinel for the file that should trigger an error,
        # keying the mock on content rather than call order.
        _UGLY_SENTINEL = "# synthetic bad plan\n"
        shutil.copy2(WELL_FORMED, tmp_path / "good.md")
        (tmp_path / "ugly.md").write_text(_UGLY_SENTINEL, encoding="utf-8")
        _real_check = __import__("plan_forge.api", fromlist=["check"]).check

        def _check_or_boom(plan_text, **kw):
            if plan_text == _UGLY_SENTINEL:
                raise RuntimeError("parse exploded")
            return _real_check(plan_text, **kw)

        monkeypatch.setattr(
            "plan_forge.adapters.cli.main.api.check", _check_or_boom,
        )
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        # Rollup: good passes (code 0), ugly errors (code 4) -> worst = 4.
        assert code == 4
        out = capsys.readouterr().out
        lines = out.strip().splitlines()
        # Both files get a line (ERROR for ugly, verdict for good)
        assert any("ERROR" in line and "ugly.md" in line for line in lines)
        assert any(
            "good.md" in line and "engineering=" in line and "epistemic=" in line
            for line in lines
        )
        # Totals line must reflect the error bucket correctly.
        totals = lines[-1]
        assert "2 plans:" in totals
        assert "1 pass" in totals
        assert "0 fail" in totals
        assert "0 vision" in totals
        assert "1 error" in totals

    def test_audit_totals_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ):
        _populate_dir(tmp_path, {
            "a.md": WELL_FORMED,
            "b.md": WELL_FORMED,
        })
        code = main([
            "audit-retroactive", str(tmp_path), "--mechanical-only",
        ])
        assert code == 0
        out = capsys.readouterr().out
        totals = out.strip().splitlines()[-1]
        # Format: "N plans: P pass, F fail, V vision, E error"
        assert "2 plans:" in totals
        assert "pass" in totals
        assert "fail" in totals
        assert "vision" in totals
        assert "error" in totals

    def test_audit_mixed_fail_and_vision_exit1(
        self, tmp_path: Path, monkeypatch,
        capsys: pytest.CaptureFixture[str],
    ):
        """Rollup with both FAIL (code 1) and VISION (code 3) files exits 1.

        Verifies that the 4>1>3>0 precedence holds when both FAIL and VISION
        are present in the batch -- FAIL must win over VISION.
        """
        from plan_forge.verdict import Verdict, EngineeringVerdict, EpistemicVerdict

        _FAIL_SENTINEL = "# fail plan\n"
        _VISION_SENTINEL = "# vision plan\n"
        (tmp_path / "a_fail.md").write_text(_FAIL_SENTINEL, encoding="utf-8")
        (tmp_path / "b_vision.md").write_text(_VISION_SENTINEL, encoding="utf-8")

        def _mock_check(plan_text, **kw):
            if plan_text == _FAIL_SENTINEL:
                return Verdict(
                    engineering=EngineeringVerdict.FAIL,
                    epistemic=EpistemicVerdict.FAIL,
                )
            return Verdict(
                engineering=EngineeringVerdict.PASS,
                epistemic=EpistemicVerdict.VISION,
            )

        monkeypatch.setattr("plan_forge.adapters.cli.main.api.check", _mock_check)
        code = main(["audit-retroactive", str(tmp_path), "--mechanical-only"])
        # Rollup: a_fail=code1, b_vision=code3 -> worst is 1 (FAIL > VISION)
        assert code == 1
        totals = capsys.readouterr().out.strip().splitlines()[-1]
        assert "2 plans:" in totals
        assert "1 fail" in totals
        assert "1 vision" in totals
