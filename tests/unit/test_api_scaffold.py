"""Unit tests for api.scaffold(): file I/O, path resolution, boundary conditions,
and name safety validation."""
from __future__ import annotations

import pytest

from plan_forge.api import scaffold


def test_scaffold_writes_md_and_returns_path(tmp_path) -> None:
    """scaffold() writes a .md file and returns its path."""
    result = scaffold("p", tmp_path)
    assert result.exists()
    assert result.suffix == ".md"
    assert result == (tmp_path / "p.md").resolve()


def test_scaffold_file_contains_title(tmp_path) -> None:
    """Written file contains the plan name in an H1 heading."""
    scaffold("my-plan", tmp_path)
    content = (tmp_path / "my-plan.md").read_text(encoding="utf-8")
    assert "# my-plan" in content


def test_scaffold_default_dir_is_cwd(tmp_path, monkeypatch) -> None:
    """scaffold() with no output_dir writes under the current directory."""
    monkeypatch.chdir(tmp_path)
    result = scaffold("p")
    assert result == (tmp_path / "p.md").resolve()
    assert result.exists()


def test_scaffold_refuses_existing(tmp_path) -> None:
    """scaffold() raises FileExistsError when target already exists; .filename is set."""
    scaffold("p", tmp_path)
    with pytest.raises(FileExistsError) as exc_info:
        scaffold("p", tmp_path)
    assert exc_info.value.filename == str((tmp_path / "p.md").resolve())


def test_scaffold_rejects_dotdot(tmp_path) -> None:
    """scaffold() raises ValueError for names containing '..'."""
    with pytest.raises(ValueError):
        scaffold("../evil", tmp_path)


def test_scaffold_rejects_slash(tmp_path) -> None:
    """scaffold() raises ValueError for names containing '/'."""
    with pytest.raises(ValueError):
        scaffold("a/b", tmp_path)


def test_scaffold_rejects_empty(tmp_path) -> None:
    """scaffold() raises ValueError for empty name."""
    with pytest.raises(ValueError):
        scaffold("", tmp_path)


def test_scaffold_rejects_unsafe_chars(tmp_path) -> None:
    """scaffold() raises ValueError for names with shell-special chars."""
    for bad in ("a b", "a*b", "a?b", "a;b", "a$b"):
        with pytest.raises(ValueError):
            scaffold(bad, tmp_path)


def test_scaffold_rejects_dot_leading(tmp_path) -> None:
    """scaffold() raises ValueError for dot-leading names (hidden files)."""
    for bad in (".hidden", "...foo", "."):
        with pytest.raises(ValueError):
            scaffold(bad, tmp_path)


def test_scaffold_rejects_dot_trailing(tmp_path) -> None:
    """scaffold() raises ValueError for trailing-dot names."""
    for bad in ("foo.", "plan."):
        with pytest.raises(ValueError):
            scaffold(bad, tmp_path)


def test_scaffold_rejects_overlong_name(tmp_path) -> None:
    """scaffold() raises ValueError for names longer than 200 chars."""
    scaffold("a" * 200, tmp_path)  # exactly at limit: accepted
    with pytest.raises(ValueError):
        scaffold("b" * 201, tmp_path)  # one over: rejected


def test_scaffold_missing_output_dir(tmp_path) -> None:
    """scaffold() raises FileNotFoundError for nonexistent output_dir."""
    with pytest.raises(FileNotFoundError):
        scaffold("p", tmp_path / "nope")


def test_scaffold_output_dir_is_file(tmp_path) -> None:
    """scaffold() raises FileNotFoundError when output_dir is a file, not a dir."""
    file_path = tmp_path / "notadir.txt"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        scaffold("p", file_path)


def test_scaffold_returns_absolute_path(tmp_path) -> None:
    """scaffold() always returns an absolute Path."""
    result = scaffold("abs-test", tmp_path)
    assert result.is_absolute()


def test_scaffold_allows_dots_and_hyphens(tmp_path) -> None:
    """scaffold() accepts names with dots and hyphens (safe slug chars)."""
    result = scaffold("plan.v1-beta", tmp_path)
    assert result.exists()
    assert result.name == "plan.v1-beta.md"


def test_scaffold_follows_symlinked_output_dir(tmp_path) -> None:
    """scaffold() follows symlinks in output_dir; file lands in resolved target."""
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    link_dir = tmp_path / "link"
    link_dir.symlink_to(real_dir)
    result = scaffold("sym-test", link_dir)
    assert result.is_absolute()
    assert (real_dir / "sym-test.md").exists()
