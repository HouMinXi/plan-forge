"""LLM clients package."""
# Import client modules so their @register decorators run. Without this
# the registry is empty and build_active_list() returns nothing.
from . import anthropic_client  # noqa: F401
from . import deepseek_client   # noqa: F401
from . import kimi_client       # noqa: F401
from . import mimo_client       # noqa: F401
