import json
from collections.abc import Callable
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

from coding_study.adapters.schema_validation import ITEM_SCHEMA_FILE, SchemaValidator
from tests.helpers import FIXTURE_TRACKS, SCHEMAS_DIRECTORY

SOURCE = "tracks/system-design/url-shortener/item.yaml"
FIXTURE_ITEMS = sorted(FIXTURE_TRACKS.glob("*/*/item.yaml"))

type Mutation = Callable[[dict[str, Any]], None]


def validator() -> SchemaValidator:
    return SchemaValidator.from_file(SCHEMAS_DIRECTORY / ITEM_SCHEMA_FILE)


def url_shortener() -> dict[str, Any]:
    return yaml.safe_load((FIXTURE_TRACKS / "system-design/url-shortener/item.yaml").read_text())


def test_schema_is_valid_draft_2020_12():
    Draft202012Validator.check_schema(
        json.loads((SCHEMAS_DIRECTORY / ITEM_SCHEMA_FILE).read_text())
    )


@pytest.mark.parametrize("path", FIXTURE_ITEMS, ids=lambda path: path.parent.name)
def test_fixture_items_are_valid(path):
    assert validator().violations(yaml.safe_load(path.read_text()), SOURCE) == []


INVALID: dict[str, tuple[Mutation, str]] = {
    "missing estimate": (lambda item: item.pop("estimate_minutes"), ""),
    "autograded track": (lambda item: item.update(track="dsa"), "track"),
    "behavioral track": (lambda item: item.update(track="behavioral"), "track"),
    "unknown key": (lambda item: item.update(hints=["think"]), ""),
    "home study guide": (
        lambda item: item["references"].update(study_guides=["~/guides/caching.md"]),
        "references.study_guides[0]",
    ),
    "absolute study guide": (
        lambda item: item["references"].update(study_guides=["/guides/caching.md"]),
        "references.study_guides[0]",
    ),
    "study guide above the root": (
        lambda item: item["references"].update(study_guides=["../caching.md"]),
        "references.study_guides[0]",
    ),
    "study guide escaping through a subdirectory": (
        lambda item: item["references"].update(study_guides=["systems/../../caching.md"]),
        "references.study_guides[0]",
    ),
    "link without scheme": (
        lambda item: item["references"].update(links=["example.com"]),
        "references.links[0]",
    ),
    "invalid related slug": (lambda item: item.update(related=["News Feed"]), "related[0]"),
}


@pytest.mark.parametrize(("mutate", "location"), INVALID.values(), ids=INVALID.keys())
def test_invalid_items_are_rejected(mutate, location):
    item = url_shortener()
    mutate(item)
    assert [issue.location for issue in validator().violations(item, SOURCE)] == [location]


@pytest.mark.parametrize(
    "guide", ["caching.md", "systems/caching.md#eviction", "caching..notes.md"]
)
def test_study_guides_are_relative_to_the_study_guides_root(guide):
    item = url_shortener()
    item["references"]["study_guides"] = [guide]
    assert validator().violations(item, SOURCE) == []
