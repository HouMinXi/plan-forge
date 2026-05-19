"""Public API: check() and scaffold()."""
from __future__ import annotations
from pathlib import Path
from .verdict import Verdict


def check(plan_text: str, **kwargs) -> Verdict:
    """Run all gates on plan_text and return a Verdict."""
    raise NotImplementedError


def scaffold(name: str, output_dir: Path | None = None) -> Path:
    """Generate a plan skeleton from the default template."""
    raise NotImplementedError
