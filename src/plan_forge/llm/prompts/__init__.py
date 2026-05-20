"""Versioned LLM prompt templates loaded from sibling .txt files."""
from __future__ import annotations
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def load(name: str) -> str:
    """Load a prompt template by name (without .txt extension)."""
    path = _PROMPT_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")
