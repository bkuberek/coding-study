"""`DEPRECATIONS` equals the Deprecations table of docs/specs/compatibility.md#deprecation, each
`json_field` entry is marked in its schema, and `commands.json` marks each deprecated flag."""

import json
from collections.abc import Mapping

import pytest

from coding_study.domain.deprecations import DEPRECATIONS, DeprecatedSurface, Deprecation
from tests.contract import surfaces
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY

SPEC = REPOSITORY_ROOT / "docs" / "specs" / "compatibility.md"
HEADING = "### Deprecations"
NO_ENTRIES = "None yet"
SCHEMA_SUFFIX = ".schema.json"

type _Row = tuple[str, str, str, str | None]


def _table_rows(text: str) -> list[list[str]]:
    """The cells of each body row of the table under the Deprecations heading."""
    lines = text.split(HEADING, 1)[1].splitlines()
    rows: list[list[str]] = []
    for line in lines:
        if line.startswith("#"):
            break
        if line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows[2:]


def _code(cell: str) -> str:
    return cell.strip("`")


def _spec_entries(text: str) -> list[_Row]:
    rows = [row for row in _table_rows(text) if row[0] != NO_ENTRIES]
    return [(row[0], _code(row[1]), row[2], _code(row[3]) or None) for row in rows]


def _registry_entries(registry: tuple[Deprecation, ...]) -> list[_Row]:
    return [(entry.surface.value, entry.name, entry.since, entry.replacement) for entry in registry]


def test_the_registry_equals_the_spec_table() -> None:
    assert _registry_entries(DEPRECATIONS) == _spec_entries(SPEC.read_text(encoding="utf-8"))


def test_the_table_says_none_yet_when_and_only_when_the_registry_is_empty() -> None:
    rows = _table_rows(SPEC.read_text(encoding="utf-8"))
    assert (len(rows) == 1 and rows[0][0] == NO_ENTRIES) == (not DEPRECATIONS)


def test_the_table_reader_reads_a_table_with_entries() -> None:
    text = (
        f"{HEADING}\n\nOne row.\n\n"
        "| Surface | Name | Since | Replacement |\n"
        "|---|---|---|---|\n"
        "| flag | `cstudy stats --since` | 0.60.0 | `cstudy stats --from` |\n"
        "| env_var | `CSTUDY_OLD` | 0.61.0 | |\n\n## Next\n"
    )
    assert _spec_entries(text) == [
        ("flag", "cstudy stats --since", "0.60.0", "cstudy stats --from"),
        ("env_var", "CSTUDY_OLD", "0.61.0", None),
    ]


@pytest.mark.parametrize(
    "entry",
    [entry for entry in DEPRECATIONS if entry.surface is DeprecatedSurface.JSON_FIELD],
    ids=lambda entry: entry.name,
)
def test_a_deprecated_json_field_is_marked_in_its_schema(entry: Deprecation) -> None:
    document, _, path = entry.name.partition(".")
    schema = json.loads(
        (SCHEMAS_DIRECTORY / "cli" / f"{document}{SCHEMA_SUFFIX}").read_text(encoding="utf-8")
    )
    fields = _fields(schema, schema, path.split("."))
    assert fields, f"{entry.name} is in no property of {document}{SCHEMA_SUFFIX}"
    assert all(field.get("deprecated") is True for field in fields)


def _fields(root: Mapping[str, object], node: Mapping[str, object], path: list[str]) -> list[dict]:
    """The schemas of the property at `path` below `node`, through `$ref`, arrays and the variants
    of `oneOf`, `anyOf` and `allOf`."""
    node = _resolved(root, node)
    if not path:
        return [dict(node)]
    found: list[dict] = []
    properties = node.get("properties")
    if isinstance(properties, Mapping) and path[0] in properties:
        found += _fields(root, properties[path[0]], path[1:])
    below = [node.get("items"), *(node.get(key) for key in ("oneOf", "anyOf", "allOf"))]
    for part in below:
        for variant in part if isinstance(part, list) else [part]:
            if isinstance(variant, Mapping):
                found += _fields(root, variant, path)
    return found


def _resolved(root: Mapping[str, object], node: Mapping[str, object]) -> Mapping[str, object]:
    reference = node.get("$ref")
    if not isinstance(reference, str):
        return node
    target: object = root
    for part in reference.removeprefix("#/").split("/"):
        target = target[part]  # type: ignore[index]
    return _resolved(root, target)  # type: ignore[arg-type]


SCHEMA = {
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "items": {"$ref": "#/$defs/row"},
        },
        "old": {"type": "string", "deprecated": True},
    },
    "$defs": {
        "row": {
            "oneOf": [
                {"type": "object", "properties": {"name": {"type": "string"}}},
                {"type": "object", "properties": {"label": {"deprecated": True}}},
            ]
        }
    },
}


def test_a_field_is_found_through_properties_arrays_references_and_variants() -> None:
    assert _fields(SCHEMA, SCHEMA, ["old"]) == [{"type": "string", "deprecated": True}]
    assert _fields(SCHEMA, SCHEMA, ["rows", "label"]) == [{"deprecated": True}]
    assert _fields(SCHEMA, SCHEMA, ["rows", "name"]) == [{"type": "string"}]
    assert _fields(SCHEMA, SCHEMA, ["rows", "absent"]) == []


def test_a_registered_flag_is_deprecated_in_the_commands_surface() -> None:
    flag = Deprecation(DeprecatedSurface.FLAG, "cstudy stats --json", "0.60.0", "--format")

    surface = surfaces.commands((flag,))
    marked = {name for name, value in surface.items() if _deprecated(value)}

    assert marked == {"cstudy stats --json"}


def test_the_commands_surface_marks_no_flag_without_a_registered_one() -> None:
    assert not any(_deprecated(value) for value in surfaces.commands().values())


def _deprecated(value: object) -> bool:
    return isinstance(value, dict) and value.get("deprecated") is True
