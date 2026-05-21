"""F1: SC-test traceability check.

Cross-references test references in SC bodies against test definitions
in the plan.  Reports orphan SC (test claimed but not defined) and
orphan test (test defined but no SC references it).
"""
from __future__ import annotations

import re

from plan_forge.parser import ParsedPlan
from plan_forge.verdict import Finding, Severity

# Regex to find test function names
_TEST_REF_RE = re.compile(r'\btest_[A-Za-z0-9_]+\b')

# Section headings that constitute "test lists" for defined_tests
_TEST_SECTION_KEYWORDS = ('test plan', 'test list', 'verification')

# Standalone word "tests" (as a whole word in a heading)
_TESTS_WORD_RE = re.compile(r'\btests\b', re.IGNORECASE)


def _heading_is_test_section(heading: str) -> bool:
    """Return True if the heading matches a test-list section keyword."""
    hl = heading.lower()
    for kw in _TEST_SECTION_KEYWORDS:
        if kw in hl:
            return True
    if _TESTS_WORD_RE.search(hl):
        return True
    return False


def check(parsed: ParsedPlan, **kwargs) -> list[Finding]:
    """Check SC-test traceability.

    Args:
        parsed: ParsedPlan to inspect.

    Returns:
        List of F1 findings (empty if both sides are absent).
    """
    # Step 1: claimed_tests per SC
    claimed_per_sc: dict[str, set[str]] = {}
    for sc in parsed.sc_table:
        refs = set(_TEST_REF_RE.findall(sc.body))
        if refs:
            claimed_per_sc[sc.full_id] = refs

    # Step 2: defined_tests from test sections and list items
    defined_tests: set[str] = set()

    # 2a: from test-list sections
    for heading, section in parsed.sections.items():
        if _heading_is_test_section(heading):
            for m in _TEST_REF_RE.finditer(section.body):
                defined_tests.add(m.group(0))

    # 2b: from markdown list items anywhere in raw_text
    for line in parsed.raw_text.splitlines():
        if re.match(r'^\s*[-*]\s+', line):
            for m in _TEST_REF_RE.finditer(line):
                defined_tests.add(m.group(0))

    # if either side is absent, skip -- absence of a test section is not F1's concern
    # (other checks cover missing required sections)
    if not claimed_per_sc or not defined_tests:
        return []

    # Build a flat set of all claimed tests for orphan_test check
    all_claimed: set[str] = set()
    for refs in claimed_per_sc.values():
        all_claimed.update(refs)

    findings: list[Finding] = []

    # Step 3: orphan SC -- claimed test not in defined_tests
    for sc in parsed.sc_table:
        sc_claims = claimed_per_sc.get(sc.full_id, set())
        for t in sorted(sc_claims):
            if t not in defined_tests:
                findings.append(Finding(
                    check_id="F1.orphan_sc",
                    severity=Severity.HIGH,
                    location=f"{sc.full_id}:line:{sc.line}",
                    message=(
                        f"{sc.full_id} references test {t!r} but no"
                        f" such test is listed in the plan"
                    ),
                    fix_hint=(
                        f"add {t} to ## Test Plan section, or fix the"
                        f" reference in {sc.full_id}"
                    ),
                ))

    # Step 4: orphan test -- defined but no SC references it
    for t in sorted(defined_tests):
        if t not in all_claimed:
            findings.append(Finding(
                check_id="F1.orphan_test",
                severity=Severity.HIGH,
                location="line:0",
                message=(
                    f"test {t!r} is defined in the plan but no SC"
                    f" references it"
                ),
                fix_hint=(
                    f"add an SC entry that covers {t}, or remove {t}"
                    f" from the test list if it is obsolete"
                ),
            ))

    return findings
