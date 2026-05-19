"""Verdict, Finding, Severity dataclasses."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    BLOCKER = "BLOCKER"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class EvidenceTier(str, Enum):
    T1_GOLD = "T1"
    T2_SILVER = "T2"
    T3_BRONZE = "T3"
    T4_UNVERIFIABLE = "T4"
    UNCLASSIFIED = "UNCLASSIFIED"


@dataclass
class Finding:
    gate: str
    severity: Severity
    message: str
    location: str = ""


@dataclass
class Verdict:
    engineering_verdict: str = "PASS"
    epistemic_verdict: str = "PASS"
    findings: list[Finding] = field(default_factory=list)
    corpus_run_id: int | None = None
    arbitration_triggered: bool = False
    tier_summary: dict = field(default_factory=dict)
    arbitration_resolution: str | None = None
