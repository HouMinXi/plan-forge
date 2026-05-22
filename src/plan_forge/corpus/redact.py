"""PII redaction for corpus entries."""
import hashlib


def compute_plan_hash(plan_text: str) -> str:
    """Return first 16 hex chars of SHA-256(plan_text encoded UTF-8)."""
    return hashlib.sha256(plan_text.encode("utf-8")).hexdigest()[:16]


def redact_plan_text(plan_text: str) -> tuple[None, str]:
    """v0 redaction: full text omission. Returns (None, hash).

    The caller stores None as plan_text and the hash as plan_hash so the
    corpus retains identity information (hash) without the plan content.
    """
    return None, compute_plan_hash(plan_text)
