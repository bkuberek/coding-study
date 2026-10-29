"""JSON Schema validation of problem files against the hand-maintained schemas in schemas/."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Self, cast

from jsonschema import Draft202012Validator, ValidationError
from jsonschema.protocols import Validator

from coding_study.domain.errors import ContentIssue

SCHEMAS_DIRECTORY = "schemas"
META_SCHEMA_FILE = "meta.schema.json"
TESTS_SCHEMA_FILE = "tests.schema.json"
ITEM_SCHEMA_FILE = "item.schema.json"
MAX_MESSAGE_LENGTH = 200
_ELLIPSIS = "..."


class SchemaValidator:
    """Builds its validator on the first `violations` call: checking a schema against the
    metaschema costs tens of milliseconds, which a command that validates nothing never pays."""

    def __init__(self, schema: Mapping[str, Any]) -> None:
        self._schema = schema
        self._validator: Validator | None = None

    @classmethod
    def from_file(cls, path: Path) -> Self:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def violations(self, document: Any, source: str) -> list[ContentIssue]:
        """Every violation in `document`, ordered by location; `source` names the file."""
        errors = sorted(self._built().iter_errors(document), key=lambda error: error.json_path)
        return [_to_issue(error, source) for error in errors]

    def _built(self) -> Validator:
        if self._validator is None:
            Draft202012Validator.check_schema(self._schema)
            self._validator = Draft202012Validator(self._schema)
        return self._validator


def _to_issue(error: ValidationError, source: str) -> ContentIssue:
    return ContentIssue(source, _location(error.json_path), _truncate(_message(error)))


def _message(error: ValidationError) -> str:
    """A `contains` of a single constant says which constant the list lacks."""
    required = cast(object, error.validator_value)
    if error.validator == "contains" and isinstance(required, dict):
        constants = cast(dict[str, Any], required)
        if list(constants) == ["const"]:
            return f"must include {json.dumps(constants['const'])}"
    return error.message


def _location(json_path: str) -> str:
    return json_path.removeprefix("$").removeprefix(".")


def _truncate(message: str) -> str:
    if len(message) <= MAX_MESSAGE_LENGTH:
        return message
    return message[: MAX_MESSAGE_LENGTH - len(_ELLIPSIS)] + _ELLIPSIS
