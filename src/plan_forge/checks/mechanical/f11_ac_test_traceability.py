"""F11: Acceptance-criteria to test-function traceability.

Scans <acceptance_criteria> blocks for references to test function names
(test_XXXX patterns) and verifies that each named function exists in
the tests/ directory. Missing functions are flagged as MEDIUM findings.
"""
from __future__ import annotations

import re
from pathlib import Path

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_TESTS_DIR = _REPO_ROOT / "tests"

_AC_RE = re.compile(r'<acceptance_criteria>(.*?)</acceptance_criteria>', re.DOTALL)
_TEST_FUNC_RE = re.compile(r'\btest_[a-z0-9_]{4,}\b')
_PYTEST_COLON_RE = re.compile(r'::(test_[a-z0-9_]{4,})\b')
_PYTEST_K_RE = re.compile(r'-k\s+(test_[a-z0-9_]{4,})\b')


def _test_function_exists(func_name: str, tests_dir: Path) -> bool:
    """Return True if func_name is defined in any .py file under tests_dir."""
    pattern = re.compile(r'\bdef\s+' + re.escape(func_name) + r'\b')
    for py_file in tests_dir.rglob("*.py"):
        try:
            if pattern.search(py_file.read_text(encoding="utf-8", errors="ignore")):
                return True
        except OSError:
            pass
    return False


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check that test functions referenced in acceptance_criteria exist.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        One F11 finding per test function name not found in tests/.
    """
    if not _TESTS_DIR.exists():
        return []

    findings: list[Finding] = []
    seen: set[str] = set()

    for block_match in _AC_RE.finditer(parsed.raw_text):
        block = block_match.group(1)
        candidates: set[str] = set()
        candidates.update(_PYTEST_COLON_RE.findall(block))
        candidates.update(_PYTEST_K_RE.findall(block))
        candidates.update(_TEST_FUNC_RE.findall(block))

        for func_name in candidates:
            if func_name in seen:
                continue
            seen.add(func_name)
            if not _test_function_exists(func_name, _TESTS_DIR):
                lineno = parsed.raw_text[:block_match.start()].count('\n') + 1
                findings.append(Finding(
                    check_id="F11.ac_test_missing",
                    severity=Severity.MEDIUM,
                    location=f"line:{lineno}",
                    message=(
                        f"acceptance_criteria references test function"
                        f" {func_name!r} not found in tests/"
                    ),
                    fix_hint=(
                        "verify the test name is correct or add the test to tests/"
                    ),
                ))
    return findings
