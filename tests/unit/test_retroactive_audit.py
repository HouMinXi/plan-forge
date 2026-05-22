"""Tests for tools/retroactive_audit.py."""
from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

# Add tools/ to sys.path so retroactive_audit can be imported without install.
# This must precede the retroactive_audit import below.
_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from retroactive_audit import DEFAULT_PATTERN, discover_plans, main  # noqa: E402


class TestDiscoverPlans:
    def test_discover_finds_and_sorts(self, tmp_path):
        """discover_plans returns sorted matching paths, excludes unrelated files."""
        (tmp_path / "02-03-PLAN.md").write_text("plan 03")
        (tmp_path / "02-01-PLAN.md").write_text("plan 01")
        (tmp_path / "02-02-PLAN.md").write_text("plan 02")
        (tmp_path / "README.md").write_text("unrelated")

        result = discover_plans(tmp_path)

        assert len(result) == 3
        assert [p.name for p in result] == [
            "02-01-PLAN.md",
            "02-02-PLAN.md",
            "02-03-PLAN.md",
        ]
        for p in result:
            assert p.name != "README.md"

    def test_discover_missing_dir(self, tmp_path):
        """Non-existent directory returns empty list."""
        nonexistent = tmp_path / "does_not_exist"
        result = discover_plans(nonexistent)
        assert result == []

    def test_discover_empty_dir(self, tmp_path):
        """Directory with no matching files returns empty list."""
        (tmp_path / "NOTES.txt").write_text("notes")
        result = discover_plans(tmp_path)
        assert result == []

    def test_discover_custom_pattern(self, tmp_path):
        """Custom pattern is respected."""
        (tmp_path / "02-01-PLAN.md").write_text("plan")
        (tmp_path / "OTHER.md").write_text("other")

        result = discover_plans(tmp_path, pattern="OTHER.md")

        assert len(result) == 1
        assert result[0].name == "OTHER.md"

    def test_discover_expands_tilde(self, tmp_path, monkeypatch):
        """discover_plans expands a leading ~ to the user home directory."""
        monkeypatch.setenv("HOME", str(tmp_path))
        plan_dir = tmp_path / "plans"
        plan_dir.mkdir()
        (plan_dir / "02-01-PLAN.md").write_text("plan")
        result = discover_plans("~/plans")
        assert len(result) == 1
        assert result[0].name == "02-01-PLAN.md"


class TestMain:
    def test_main_no_plans_returns_1(self, tmp_path, capsys):
        """Empty directory returns exit code 1."""
        rc = main([str(tmp_path)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "no plans found" in out

    def test_main_lists_plans_returns_0(self, tmp_path, capsys):
        """Directory with plans returns exit code 0 and prints paths."""
        (tmp_path / "02-01-PLAN.md").write_text("plan 01")
        (tmp_path / "02-02-PLAN.md").write_text("plan 02")

        rc = main([str(tmp_path)])

        assert rc == 0
        out = capsys.readouterr().out
        assert "02-01-PLAN.md" in out
        assert "02-02-PLAN.md" in out

    def test_main_missing_dir_returns_1(self, tmp_path, capsys):
        """Non-existent directory returns exit code 1."""
        rc = main([str(tmp_path / "missing")])
        assert rc == 1

    def test_main_custom_pattern(self, tmp_path, capsys):
        """--pattern flag overrides default."""
        (tmp_path / "02-01-PLAN.md").write_text("plan")
        (tmp_path / "MY-SPEC.md").write_text("spec")

        rc = main([str(tmp_path), "--pattern", "MY-SPEC.md"])

        assert rc == 0
        out = capsys.readouterr().out
        assert "MY-SPEC.md" in out
        assert "02-01-PLAN.md" not in out

    def test_main_output_notes_audit_not_implemented(self, tmp_path, capsys):
        """Summary line tells the user that running checks is not in this runner."""
        (tmp_path / "02-01-PLAN.md").write_text("plan")

        main([str(tmp_path)])

        out = capsys.readouterr().out
        assert "not implemented" in out


class TestDefaultPattern:
    def test_default_pattern_matches_forge_naming(self):
        """DEFAULT_PATTERN matches real forge plan names."""
        assert fnmatch.fnmatch("02-01-PLAN.md", DEFAULT_PATTERN)
        assert fnmatch.fnmatch("02-06-PLAN.md", DEFAULT_PATTERN)

    def test_default_pattern_excludes_unrelated(self):
        """DEFAULT_PATTERN does not match unrelated filenames."""
        assert not fnmatch.fnmatch("README.md", DEFAULT_PATTERN)
        assert not fnmatch.fnmatch("LEARNINGS.md", DEFAULT_PATTERN)
        assert not fnmatch.fnmatch("01-01-PLAN.md", DEFAULT_PATTERN)
