"""Verdict, Finding, Severity, and related dataclasses.

Field ordering: non-defaulted fields precede defaulted ones (Python
dataclass requirement).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Finding severity levels.

    No INFO level -- only BLOCKER/HIGH/MEDIUM/LOW.
    """
    BLOCKER = "BLOCKER"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EngineeringVerdict(str, Enum):
    """Two-value engineering verdict derived from F1-F7 + PBR + G mechanical."""
    PASS = "PASS"
    FAIL = "FAIL"


class EpistemicVerdict(str, Enum):
    """Three-value epistemic verdict derived from G1-G10 aggregation rules."""
    PASS = "PASS"
    FAIL = "FAIL"
    VISION = "VISION"


class EvidenceTier(str, Enum):
    """Provenance tier for LLM-fetched evidence (G10).

    T4_SUSPECT marks evidence requiring extra scrutiny (not T4_UNVERIFIABLE,
    which conflates absence of data with presence of a flaw).
    UNCLASSIFIED is the default; post-processing upgrades U to T1-T4
    monotonically.
    """
    T1_GOLD = "T1"
    T2_SILVER = "T2"
    T3_BRONZE = "T3"
    T4_SUSPECT = "T4"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass
class LLMEvidence:
    """Evidence record from a single LLM provider call.

    Non-defaulted fields come first (Python dataclass requirement).
    tier defaults to UNCLASSIFIED so G4/G6/G8/G9 callers do not need
    to know G10 output schema; G10 fills tier in post-processing.
    """
    # Required (no defaults)
    provider: str          # "anthropic" / "kimi" / "deepseek" / "mimo"
    model: str             # e.g., "claude-opus-4-7"
    verdict: str           # provider's individual verdict string
    reasoning: str
    prompt_version: str    # filename of prompt used (without extension)
    run_id: int            # FK to plan_runs; set by corpus recorder
    # Optional with defaults
    cited_instances: list[dict] = field(default_factory=list)
    search_evidence: list[dict] = field(default_factory=list)
    tier: EvidenceTier = EvidenceTier.UNCLASSIFIED


@dataclass
class Finding:
    """A single check finding.

    Non-defaulted fields come first (Python dataclass requirement).
    fix_hint defaults to "" because many mechanical findings have no
    specific fix beyond the message itself.
    """
    # Required (no defaults)
    check_id: str      # "F1" / "G3" / "G6.mechanical" / "G6.llm" / etc.
    severity: Severity
    location: str
    message: str
    # Optional with defaults
    fix_hint: str = ""
    llm_evidence: list[LLMEvidence] = field(default_factory=list)
    evidence_tier_summary: dict = field(default_factory=dict)


@dataclass
class Verdict:
    """Final verdict returned by api.check().

    Non-defaulted fields come first (Python dataclass requirement).
    arbitration_resolution canonical vocab: "verified" / "unverified" /
    "deferred" / "abstain" (4-value set; matches arbitrations.human_verdict
    CHECK constraint in corpus schema and bundle.py prompt per M-1 fix).
    """
    # Required (no defaults)
    engineering: EngineeringVerdict
    epistemic: EpistemicVerdict
    # Optional with defaults
    findings: list[Finding] = field(default_factory=list)
    corpus_run_id: int | None = None
    arbitration_triggered: bool = False
    tier_summary: dict = field(default_factory=dict)
    active_providers: list[str] = field(default_factory=list)
    arbitration_resolution: str | None = None

    def summary(self) -> str:
        """Human-readable summary of verdict and finding counts by severity.

        Intended for CLI display and downstream adapters.
        Lists LLM providers only when active_providers is non-empty.
        """
        counts: dict[Severity, int] = {s: 0 for s in Severity}
        for f in self.findings:
            counts[f.severity] += 1

        lines = [
            f"Engineering: {self.engineering.value}",
            f"Epistemic: {self.epistemic.value}",
            f"Findings: {len(self.findings)} total",
            f"  BLOCKER: {counts[Severity.BLOCKER]}",
            f"  HIGH: {counts[Severity.HIGH]}",
            f"  MEDIUM: {counts[Severity.MEDIUM]}",
            f"  LOW: {counts[Severity.LOW]}",
        ]
        if self.active_providers:
            lines.append(f"LLM providers: {', '.join(self.active_providers)}")
        return "\n".join(lines)
