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
from coding_study.domain.config_keys import KEY_TITLES, ConfigKey, KeyKind
from coding_study.domain.taxonomy import DOMAINS

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


def test_every_key_has_a_title_and_no_title_outlives_its_key():
    assert set(KEY_TITLES) == {key.name for key in CONFIG_KEYS}


def test_no_two_keys_of_a_section_read_the_same():
    labels = [(title.section, title.label) for title in KEY_TITLES.values()]
    assert len(labels) == len(set(labels))


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


def test_the_profile_keys_are_lists_of_every_value_but_general_for_roles():
    roles, domains = BY_NAME["profile.job_roles"], BY_NAME["profile.domains"]
    assert (roles.kind, domains.kind) == (KeyKind.CHOICES, KeyKind.CHOICES)
    assert list(roles.choices) == roles.default
    assert list(domains.choices) == domains.default
    assert "general" not in roles.choices
    assert domains.choices == DOMAINS


def test_the_profile_keys_share_one_section_with_their_own_labels():
    titles = [KEY_TITLES["profile.job_roles"], KEY_TITLES["profile.domains"]]
    assert [(title.section, title.label) for title in titles] == [
        ("profile", "Job roles"),
        ("profile", "Domains"),
    ]


def test_the_template_shows_the_profile_keys_at_their_defaults():
    template = config_template()
    assert "[profile]" in template
    assert '# job_roles = ["backend", "platform", ' in template
    assert '# domains = ["algorithms", "backend", ' in template


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


AI_KEYS = [
    "ai.enabled",
    "ai.routing",
    "ai.model",
    "ai.fast",
    "ai.strong",
    "ai.daily_token_cap",
]


def test_the_ai_table_has_six_keys_in_the_order_of_the_file_after_the_study_guides():
    names = [key.name for key in CONFIG_KEYS]
    assert names[-len(AI_KEYS) - 1 :] == ["study_guides.root", *AI_KEYS]


def test_only_the_ai_keys_are_preview():
    assert [key.name for key in CONFIG_KEYS if key.preview] == AI_KEYS


def test_the_ai_keys_share_one_section_with_the_titles_of_the_spec():
    assert [(KEY_TITLES[name].section, KEY_TITLES[name].label) for name in AI_KEYS] == [
        ("ai", "Turn on AI (preview)"),
        ("ai", "Routing"),
        ("ai", "Model"),
        ("ai", "Fast tier"),
        ("ai", "Strong tier"),
        ("ai", "Daily token cap"),
    ]


def test_the_ai_keys_have_the_kinds_and_defaults_of_the_spec():
    shapes = {name: (BY_NAME[name].kind, BY_NAME[name].default) for name in AI_KEYS}
    assert shapes == {
        "ai.enabled": (KeyKind.BOOLEAN, False),
        "ai.routing": (KeyKind.CHOICE, "fixed"),
        "ai.model": (KeyKind.TEXT, None),
        "ai.fast": (KeyKind.TEXT, None),
        "ai.strong": (KeyKind.TEXT, None),
        "ai.daily_token_cap": (KeyKind.INTEGER, 500_000),
    }
    assert BY_NAME["ai.routing"].choices == ("fixed", "auto")


@pytest.mark.parametrize("name", ["ai.model", "ai.fast", "ai.strong"])
def test_a_model_key_shows_an_example_with_a_provider_and_has_no_default(name):
    key = BY_NAME[name]
    assert key.default is None
    assert str(key.example).split(":")[0] in {"anthropic", "google", "openai", "openrouter"}


def test_the_template_lists_the_ai_table_with_its_defaults_and_examples():
    template = config_template()
    assert "[ai]" in template
    assert "# enabled = false" in template
    assert '# routing = "fixed"' in template
    assert '# model = "anthropic:' in template
    assert "# daily_token_cap = 500000" in template
