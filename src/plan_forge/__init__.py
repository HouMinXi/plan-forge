"""plan-forge: epistemological gate enforcer for plan documents."""
from .api import check, scaffold
from .verdict import Verdict, Finding, Severity

__version__ = "0.1.0a1"
__all__ = ["check", "scaffold", "Verdict", "Finding", "Severity"]
