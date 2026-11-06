"""The description of the config's keys against the parser (docs/specs/cli.md#configuration): what
the Settings view draws can't miss a key, or hold one the parser refuses."""

import re
import tomllib
from collections.abc import Mapping

import pytest

from coding_study.adapters.toml_config import (
    CONFIG_KEYS,
    config_from_mapping,
    config_template,
    parsed_key_names,
)
from coding_study.domain.config import Config
from coding_study.domain.config_keys import ConfigKey, KeyKind

SOURCE = "test"
KEY_LINE = re.compile(r"^# \w+ = ")
BY_NAME = {key.name: key for key in CONFIG_KEYS}


def nested(values: Mapping[str, object]) -> dict[str, object]:
    document: dict[str, object] = {}
    for name, value in values.items():
        table, _, short = name.rpartition(".")
        target = document.setdefault(table, {}) if table else document
        target[short] = value  # type: ignore[index]
    return document


def test_the_description_holds_exactly_the_keys_the_parser_reads():
    assert {key.name for key in CONFIG_KEYS} == parsed_key_names()


def test_every_key_has_help_and_says_when_it_applies():
    missing = [key.name for key in CONFIG_KEYS if not key.help or not key.applies]
    assert missing == []


def test_the_described_defaults_parse_to_the_default_config():
    values = {key.name: key.default for key in CONFIG_KEYS if key.default is not None}
    assert config_from_mapping(nested(values), SOURCE) == Config()


@pytest.mark.parametrize(
    "key", [key for key in CONFIG_KEYS if key.default is None], ids=lambda key: key.name
)
def test_the_example_of_a_key_without_a_default_parses(key: ConfigKey):
    assert config_from_mapping(nested({key.name: key.example}), SOURCE) != Config()


def test_a_choice_names_every_allowed_value():
    assert BY_NAME["default_lang"].choices == (
        "python",
        "typescript",
        "java",
        "kotlin",
        "go",
        "rust",
    )


def test_the_tracks_are_a_list_of_choices():
    key = BY_NAME["next.tracks"]
    assert (key.kind, key.default) == (KeyKind.CHOICES, ["dsa"])


def test_only_auto_commit_is_reserved():
    assert [key.name for key in CONFIG_KEYS if key.reserved] == ["done.auto_commit"]


def test_the_commented_template_parses_to_the_defaults():
    assert config_from_mapping(tomllib.loads(config_template()), SOURCE) == Config()


@pytest.mark.parametrize("key", CONFIG_KEYS, ids=lambda key: key.name)
def test_the_template_names_every_key(key: ConfigKey):
    short = key.name.rpartition(".")[2]
    assert f"# {short} = " in config_template()


def test_the_template_says_a_changed_progress_db_moves_nothing():
    assert "does not move" in config_template()


def test_uncommenting_every_key_of_the_template_keeps_the_schedule():
    lines = [
        line.removeprefix("# ") if KEY_LINE.match(line) else line
        for line in config_template().splitlines()
    ]
    config = config_from_mapping(tomllib.loads("\n".join(lines)), SOURCE)
    assert config.schedule == Config().schedule
