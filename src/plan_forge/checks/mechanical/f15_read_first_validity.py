"""F15: Read-first file validity check.

Verifies that each path listed in a <read_first> block exists on disk,
excluding paths listed in the plan's files_modified frontmatter field
(those may not exist yet) and glob patterns containing * or { }.
"""
from __future__ import annotations

import re
from pathlib import Path

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_READ_FIRST_RE = re.compile(r'<read_first>(.*?)</read_first>', re.DOTALL)
_PATH_LINE_RE = re.compile(r'^\s*-\s+(\S+)', re.MULTILINE)
_BOM = chr(0xFEFF)


def _is_glob_pattern(path_str: str) -> bool:
    """Return True if path_str contains glob wildcards."""
    return any(c in path_str for c in ('*', '{', '}'))


def _extract_files_modified(raw_text: str) -> set[str]:
    """Parse files_modified list from YAML frontmatter."""
    lines = raw_text.splitlines()
    if not lines or lines[0].strip().lstrip(_BOM) != '---':
        return set()
    result: set[str] = set()
    collecting = False
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == '---':
            break
        if stripped.startswith('files_modified:'):
            collecting = True
            continue
        if collecting:
            m = re.match(r'^\s{2,}-\s+(.+)', line)
            if m:
                result.add(m.group(1).strip())
            elif stripped and not stripped.startswith((' ', '\t', '-')):
                collecting = False
    return result


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check that all <read_first> paths exist on disk.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        One F15 finding per path that is missing from disk.
    """
    files_modified = _extract_files_modified(parsed.raw_text)
    findings: list[Finding] = []
    for block_match in _READ_FIRST_RE.finditer(parsed.raw_text):
        block = block_match.group(1)
        for path_match in _PATH_LINE_RE.finditer(block):
            path_str = path_match.group(1).strip()
            if _is_glob_pattern(path_str):
                continue
            if path_str in files_modified:
                continue
            p = (
                Path(path_str)
                if Path(path_str).is_absolute()
                else _REPO_ROOT / path_str
            )
            if not p.exists():
                lineno = parsed.raw_text[:block_match.start()].count('\n') + 1
                findings.append(Finding(
                    check_id="F15.read_first_missing",
                    severity=Severity.MEDIUM,
                    location=f"line:{lineno}",
                    message=f"read_first path not found on disk: {path_str!r}",
                    fix_hint=(
                        "update the path or move it to files_modified"
                        " if created by this plan"
                    ),
                ))
    return findings
