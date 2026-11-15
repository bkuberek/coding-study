"""The Problems view names each filter by its key and writes the flag of `cstudy list` as `--` and
the key, or the name `FLAG_NAMES` gives it (`tools/web-ui/src/page/commands.ts`), so every key must
be a flag of the command it mirrors, and its columns are the ones the preferences accept
(docs/specs/web-ui.md#problems-view)."""

import re

import pytest
import typer.main

from coding_study.domain.preferences import DEFAULT_PROBLEM_COLUMNS, PROBLEM_COLUMNS
from coding_study.entrypoints import cli
from tests.helpers import REPOSITORY_ROOT

PAGE = REPOSITORY_ROOT / "tools" / "web-ui" / "src" / "page"
FLAG_NAMES = {"checked": "checked-by"}
"""The keys whose flag is not their name, as `commands.ts` holds them."""


def keys_declared(source_file: str, constant: str) -> list[str]:
    text = (PAGE / source_file).read_text()
    declaration = re.search(rf"{constant}[^=]*=\s*\[([^\]]*)\]", text)
    assert declaration is not None, f"{constant} is not declared in {source_file}"
    return re.findall(r'"([a-z_]+)"', declaration.group(1))


def flags_of(command_name: str) -> set[str]:
    group = typer.main.get_group(cli.app)
    return {
        option for parameter in group.commands[command_name].params for option in parameter.opts
    }


def test_the_flag_names_are_the_ones_commands_ts_holds():
    text = (PAGE / "commands.ts").read_text()
    declaration = re.search(r"FLAG_NAMES[^=]*=\s*\{([^}]*)\}", text)
    assert declaration is not None
    assert dict(re.findall(r'(\w+): "([a-z-]+)"', declaration.group(1))) == FLAG_NAMES


def test_the_page_filters_by_the_labels():
    assert {"domain", "role", "scope"} <= set(keys_declared("routes.ts", "FILTER_KEYS"))


@pytest.mark.parametrize("key", keys_declared("routes.ts", "FILTER_KEYS"))
def test_every_filter_key_is_a_flag_of_cstudy_list(key):
    assert f"--{FLAG_NAMES.get(key, key)}" in flags_of("list")


@pytest.mark.parametrize("key", keys_declared("commands.ts", "NEXT_FILTERS"))
def test_every_filter_the_next_card_passes_is_a_flag_of_cstudy_next(key):
    assert f"--{key}" in flags_of("next")


@pytest.mark.parametrize("key", keys_declared("commands.ts", "LEARN_FILTERS"))
def test_every_filter_the_guides_view_names_is_a_flag_of_cstudy_learn(key):
    assert f"--{key}" in flags_of("learn")


def test_the_page_offers_the_columns_the_preferences_accept():
    assert keys_declared("problems-model.ts", "PROBLEM_COLUMNS") == list(PROBLEM_COLUMNS)


def test_the_page_resets_to_the_columns_the_preferences_default_to():
    assert keys_declared("problems-model.ts", "DEFAULT_COLUMNS") == list(DEFAULT_PROBLEM_COLUMNS)
