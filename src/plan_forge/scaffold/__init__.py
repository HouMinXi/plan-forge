"""Plan skeleton rendering. render() returns markdown; api.scaffold writes it."""
from __future__ import annotations
from pathlib import Path
import jinja2

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=False,  # markdown output; HTML escaping not applicable
    keep_trailing_newline=True,
)


def render(name: str) -> str:
    """Render the default plan skeleton with the given plan title.

    Raises:
        RuntimeError: the bundled template is missing (corrupted install).
    """
    try:
        return _ENV.get_template("default.md.j2").render(plan_name=name)
    except jinja2.TemplateNotFound as e:
        raise RuntimeError(f"scaffold template missing -- package may be corrupted: {e}") from e
