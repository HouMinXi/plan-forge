"""Tests for CLI argparse skeleton and dispatch (Phase 1)."""
from __future__ import annotations

import pytest

from plan_forge.adapters.cli.main import main


class TestArgparseHelp:
    """Verify --help exits zero and subcommand help works."""

    def test_top_help_exits_zero(self, capsys: pytest.CaptureFixture[str]):
        with pytest.raises(SystemExit) as exc_info:
            main(["--help"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "plan-forge" in out

    @pytest.mark.parametrize("subcmd", ["check", "scaffold", "audit-retroactive"])
    def test_each_subcommand_help_exits_zero(
        self, subcmd: str, capsys: pytest.CaptureFixture[str],
    ):
        with pytest.raises(SystemExit) as exc_info:
            main([subcmd, "--help"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert subcmd in out


class TestArgparseErrors:
    """Verify missing/invalid subcommand yields exit 2."""

    def test_no_command_errors(self):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2


class TestExceptGuard:
    """Verify the main except-guard catches handler exceptions."""

    def test_unexpected_exception_exits_4(
        self, tmp_path, monkeypatch, capsys: pytest.CaptureFixture[str],
    ):
        plan_file = tmp_path / "good.md"
        plan_file.write_text("# Test\n", encoding="utf-8")

        def _boom(*_a, **_kw):
            raise RuntimeError("kaboom")

        monkeypatch.setattr("plan_forge.adapters.cli.main.api.check", _boom)
        code = main(["check", str(plan_file), "--mechanical-only"])
        assert code == 4
        err = capsys.readouterr().err
        assert "kaboom" in err
