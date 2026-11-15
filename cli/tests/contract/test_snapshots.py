"""The public surfaces equal their snapshots (docs/specs/compatibility.md#snapshots).

A failure lists the removed, changed and added entries apart. An intended change is accepted with
`CSTUDY_WRITE_SNAPSHOTS=1 uv run pytest -q tests/contract`, which writes the snapshots again.
"""

import json
from pathlib import Path

import pytest

from coding_study.adapters.toml_config import CONFIG_KEYS, parsed_key_names
from coding_study.entrypoints.commands._events import EVENTS_VERSION
from tests.contract import surfaces
from tests.contract.snapshot_files import (
    REGENERATE_HINT,
    WRITE_VARIABLE,
    SurfaceDiff,
    check_snapshot,
    diff_surfaces,
    read_snapshot,
    report,
    snapshot_text,
    writing_snapshots,
)
from tests.helpers import REPOSITORY_ROOT

EVENT_SCHEMAS = ("events.schema.json", "dev-events.schema.json")


def test_commands_flags_and_choices_are_the_snapshot() -> None:
    check_snapshot("commands.json", surfaces.commands())


def test_exit_codes_are_the_snapshot() -> None:
    check_snapshot("exit-codes.json", surfaces.exit_codes())


def test_config_keys_are_the_snapshot() -> None:
    check_snapshot("config-keys.json", surfaces.config_keys())


def test_every_key_the_parser_reads_is_a_described_config_key() -> None:
    assert parsed_key_names() == {key.name for key in CONFIG_KEYS}


def test_environment_variables_are_the_snapshot() -> None:
    check_snapshot("environment.json", surfaces.environment())


def test_marker_is_the_snapshot(tmp_path: Path) -> None:
    check_snapshot("marker.json", surfaces.marker(tmp_path))


@pytest.mark.parametrize("schema", EVENT_SCHEMAS)
def test_event_streams_are_version_1(schema: str) -> None:
    document = json.loads((REPOSITORY_ROOT / "schemas" / schema).read_text(encoding="utf-8"))
    assert document["$defs"]["version"]["const"] == 1


def test_events_are_written_as_version_1() -> None:
    assert EVENTS_VERSION == 1


@pytest.fixture
def checking(monkeypatch: pytest.MonkeyPatch) -> None:
    """Snapshots are compared, even in a run that writes the real ones."""
    monkeypatch.delenv(WRITE_VARIABLE, raising=False)


def test_the_diff_names_removed_changed_and_added_entries_apart() -> None:
    snapshot = {"gone": 1, "same": 2, "moved": {"a": 1}}
    live = {"same": 2, "moved": {"a": 2}, "new": True}

    diff = diff_surfaces(snapshot, live)

    assert diff == SurfaceDiff(removed=("gone",), changed=("moved",), added=("new",))
    assert not diff.empty
    text = report(diff, snapshot, live)
    assert text.splitlines() == [
        "removed (1):",
        "  gone: 1",
        "changed (1):",
        '  moved: {"a": 1} -> {"a": 2}',
        "added (1):",
        "  new: true",
        REGENERATE_HINT,
    ]


def test_equal_surfaces_have_an_empty_diff() -> None:
    assert diff_surfaces({"a": 1}, {"a": 1}).empty


def test_a_snapshot_that_differs_fails_with_the_report(checking: None, tmp_path: Path) -> None:
    (tmp_path / "surface.json").write_text(snapshot_text({"old": 1, "kept": 1}), encoding="utf-8")

    with pytest.raises(AssertionError) as failure:
        check_snapshot("surface.json", {"kept": 2, "fresh": 3}, tmp_path)

    message = str(failure.value)
    assert "removed (1):\n  old: 1" in message
    assert "changed (1):\n  kept: 1 -> 2" in message
    assert "added (1):\n  fresh: 3" in message


def test_a_missing_snapshot_fails_with_how_to_write_it(checking: None, tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match=WRITE_VARIABLE):
        check_snapshot("surface.json", {"a": 1}, tmp_path)


def test_a_snapshot_that_is_not_in_its_stable_form_fails(checking: None, tmp_path: Path) -> None:
    (tmp_path / "surface.json").write_text('{"b": 1, "a": 2}', encoding="utf-8")

    with pytest.raises(AssertionError, match="stable form"):
        check_snapshot("surface.json", {"a": 2, "b": 1}, tmp_path)


def test_snapshots_are_sorted_indented_and_end_with_a_newline() -> None:
    text = snapshot_text({"b": [1], "a": {"d": 1, "c": None}})

    assert text == '{\n  "a": {\n    "c": null,\n    "d": 1\n  },\n  "b": [\n    1\n  ]\n}\n'


def test_writing_snapshots_replaces_them_with_the_live_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "snapshots"
    monkeypatch.setenv(WRITE_VARIABLE, "1")

    check_snapshot("surface.json", {"b": 2, "a": 1}, directory)

    assert read_snapshot(directory / "surface.json") == {"a": 1, "b": 2}
    assert (directory / "surface.json").read_text(encoding="utf-8") == snapshot_text(
        {"a": 1, "b": 2}
    )
    monkeypatch.delenv(WRITE_VARIABLE)
    check_snapshot("surface.json", {"a": 1, "b": 2}, directory)


def test_snapshots_are_written_only_when_the_variable_is_1() -> None:
    assert writing_snapshots({WRITE_VARIABLE: "1"})
    assert not writing_snapshots({WRITE_VARIABLE: "0"})
    assert not writing_snapshots({})
