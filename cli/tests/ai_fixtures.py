"""The recorded provider replies of `tests/fixtures/ai/<provider>/`, written by hand from each
provider's documented response shape (docs/specs/ai.md#testing)."""

import json
from pathlib import Path
from typing import Any

from coding_study.domain.ai import Provider

FIXTURES = Path(__file__).parent / "fixtures" / "ai"
SECRET = "sk-test-0123456789"
"""The key the error fixtures echo, as a provider's own error text may."""


def recorded(provider: Provider, name: str) -> Any:
    """The JSON of `<name>.json`."""
    return json.loads((FIXTURES / provider.value / f"{name}.json").read_text(encoding="utf-8"))
