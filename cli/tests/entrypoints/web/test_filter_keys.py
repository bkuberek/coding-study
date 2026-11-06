"""The Problems view names each filter by its key and writes the flag of `cstudy list` as `--` and
the key (`tools/web-ui/src/page/commands.ts`), so every key must be a flag of the command it
mirrors (docs/specs/web-ui.md#problems-view)."""

import re

import pytest
import typer.main

from coding_study.entrypoints import cli
from tests.helpers import REPOSITORY_ROOT

PAGE = REPOSITORY_ROOT / "tools" / "web-ui" / "src" / "page"


def keys_declared(source_file: str, constant: str) -> list[str]:
    text = (PAGE / source_file).read_text()
    declaration = re.search(rf"{constant}[^=]*=\s*\[([^\]]*)\]", text)
    assert declaration is not None, f"{constant} is not declared in {source_file}"
    return re.findall(r'"([a-z]+)"', declaration.group(1))


def flags_of(command_name: str) -> set[str]:
    group = typer.main.get_group(cli.app)
    return {
        option for parameter in group.commands[command_name].params for option in parameter.opts
    }


def test_the_page_filters_by_the_labels():
    assert {"domain", "role", "scope"} <= set(keys_declared("routes.ts", "FILTER_KEYS"))


@pytest.mark.parametrize("key", keys_declared("routes.ts", "FILTER_KEYS"))
def test_every_filter_key_is_a_flag_of_cstudy_list(key):
    assert f"--{key}" in flags_of("list")


@pytest.mark.parametrize("key", keys_declared("commands.ts", "NEXT_FILTERS"))
def test_every_filter_the_next_card_passes_is_a_flag_of_cstudy_next(key):
    assert f"--{key}" in flags_of("next")
