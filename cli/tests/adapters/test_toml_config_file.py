"""`config.toml` written from Settings (docs/specs/web-ui.md#settings-view): only the changed keys,
keeping everything else; refused when it would not load."""

import re
import stat
import tomllib
from pathlib import Path

import pytest

from coding_study.adapters.toml_config_file import TomlConfigFile
from coding_study.domain.errors import ConfigError, UsageError

COMMENTED = """\
# My cstudy settings, keep this line
default_lang = "go"    # I practise in Go

# Spaced repetition
[schedule]
# Long enough for me
max_interval_days = 90 # three months
penalize_suboptimal = false

[bench]
reps = 9
"""


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "coding-study" / "config.toml"


def write(path: Path, text: str) -> TomlConfigFile:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return TomlConfigFile(path)


def key(file: TomlConfigFile, name: str):
    return next(state for state in file.read().keys if state.key.name == name)


# Reading


def test_a_missing_file_reads_as_the_defaults(path):
    view = TomlConfigFile(path).read()
    assert (view.exists, view.issues, key(TomlConfigFile(path), "bench.reps").value) == (
        False,
        (),
        7,
    )


def test_a_key_set_in_the_file_shows_its_value_and_keeps_its_default(path):
    state = key(write(path, COMMENTED), "bench.reps")
    assert (state.value, state.is_set, state.key.default) == (9, True, 7)


def test_a_key_not_in_the_file_shows_the_default_as_unset(path):
    state = key(write(path, COMMENTED), "bench.memory")
    assert (state.value, state.is_set) == (True, False)


def test_a_key_without_a_default_reads_as_null(path):
    assert key(write(path, ""), "hang_guard.ms").value is None


def test_a_file_that_does_not_parse_says_so(path):
    view = write(path, "reps = = 3\n").read()
    assert (view.writable, len(view.issues)) == (False, 1)


def test_an_invalid_value_is_reported_and_the_file_stays_writable(path):
    view = write(path, "[bench]\nreps = 0\n").read()
    assert (view.writable, view.issues) == (True, ("bench.reps: expected a positive integer",))


def test_an_invalid_value_shows_as_written(path):
    assert key(write(path, '[bench]\nreps = "many"\n'), "bench.reps").value == "many"


# Writing keeps the rest of the file


def test_a_changed_value_keeps_every_comment_and_the_formatting(path):
    file = write(path, COMMENTED)
    file.apply({"schedule.max_interval_days": 120})
    assert path.read_text() == COMMENTED.replace(
        "max_interval_days = 90 # three months", "max_interval_days = 120 # three months"
    )


def test_a_key_of_a_table_that_is_there_joins_it(path):
    file = write(path, COMMENTED)
    file.apply({"bench.memory": False})
    assert tomllib.loads(path.read_text())["bench"] == {"reps": 9, "memory": False}


def test_a_key_of_a_table_that_is_not_there_makes_the_table(path):
    file = write(path, COMMENTED)
    file.apply({"hang_guard.ms": 5000})
    assert tomllib.loads(path.read_text())["hang_guard"] == {"ms": 5000}


def test_a_top_level_key_stays_above_the_tables(path):
    file = write(path, COMMENTED)
    file.apply({"open_on_start": False})
    document = tomllib.loads(path.read_text())
    assert (document["open_on_start"], "open_on_start" in document["bench"]) == (False, False)


def test_a_dotted_key_in_the_file_is_changed_in_place(path):
    file = write(path, "schedule.max_interval_days = 90 # mine\n")
    file.apply({"schedule.max_interval_days": 60})
    assert path.read_text() == "schedule.max_interval_days = 60 # mine\n"


def test_an_inline_table_is_changed_in_place(path):
    file = write(path, "schedule = { max_interval_days = 90 }\n")
    file.apply({"schedule.max_interval_days": 60})
    assert tomllib.loads(path.read_text()) == {"schedule": {"max_interval_days": 60}}


def test_a_list_value_is_written_as_a_list(path):
    file = write(path, "")
    file.apply({"next.tracks": ["dsa", "lld"]})
    assert tomllib.loads(path.read_text()) == {"next": {"tracks": ["dsa", "lld"]}}


def test_null_removes_the_key_and_returns_it_to_its_default(path):
    file = write(path, COMMENTED)
    file.apply({"bench.reps": None})
    assert (tomllib.loads(path.read_text())["bench"], key(file, "bench.reps").value) == ({}, 7)


def test_null_on_a_key_that_is_not_there_writes_nothing(path):
    file = write(path, COMMENTED)
    before = path.stat().st_mtime_ns
    assert (file.apply({"bench.memory": None}), path.stat().st_mtime_ns) == ((), before)


def test_a_value_equal_to_the_one_in_force_writes_nothing(path):
    file = write(path, COMMENTED)
    before = path.stat().st_mtime_ns
    assert (file.apply({"schedule.max_interval_days": 90}), path.stat().st_mtime_ns) == ((), before)


def test_the_default_of_a_key_not_in_the_file_is_not_written(path):
    file = write(path, COMMENTED)
    file.apply({"bench.memory": True})
    assert path.read_text() == COMMENTED


def test_apply_names_the_keys_it_changed(path):
    file = write(path, COMMENTED)
    changed = file.apply({"bench.reps": 9, "bench.memory": False, "open_on_start": False})
    assert changed == ("bench.memory", "open_on_start")


def test_an_integer_never_equals_the_boolean_it_compares_equal_to(path):
    file = write(path, "[bench]\nreps = 1\n")
    with pytest.raises(UsageError):
        file.apply({"bench.reps": True})


def test_a_file_that_is_missing_is_created_with_its_folder(path):
    TomlConfigFile(path).apply({"schedule.max_interval_days": 30})
    assert tomllib.loads(path.read_text()) == {"schedule": {"max_interval_days": 30}}


def test_no_change_to_a_missing_file_creates_nothing(path):
    TomlConfigFile(path).apply({"bench.memory": True})
    assert not path.exists()


def test_the_mode_of_the_file_is_kept(path):
    file = write(path, COMMENTED)
    path.chmod(0o600)
    file.apply({"bench.reps": 3})
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_a_link_to_the_file_stays_a_link(tmp_path, path):
    target = tmp_path / "dotfiles" / "cstudy.toml"
    target.parent.mkdir()
    target.write_text(COMMENTED)
    path.parent.mkdir(parents=True)
    path.symlink_to(target)
    TomlConfigFile(path).apply({"bench.reps": 3})
    assert (path.is_symlink(), tomllib.loads(target.read_text())["bench"]["reps"]) == (True, 3)


def test_no_temporary_file_stays_behind(path):
    write(path, COMMENTED).apply({"bench.reps": 3})
    assert [found.name for found in path.parent.iterdir()] == ["config.toml"]


# Refusals


@pytest.mark.parametrize(
    ("name", "value", "issue"),
    [
        ("bench.reps", 0, "bench.reps: expected a positive integer"),
        ("default_lang", "scala", "default_lang: expected one of"),
        ("next.tracks", ["chess"], 'next.tracks: unknown track "chess"'),
        ("time_limit.value", "fast", 'time_limit.value: invalid time limit "fast"'),
        ("study_guides.root", "guides", "study_guides.root: expected an absolute path"),
        ("schedule.again_interval_days", -1, "schedule.again_interval_days: expected a positive"),
        ("schedule.mastered_interval_days", 200, "schedule.mastered_interval_days: 200 is above"),
    ],
)
def test_a_value_the_cli_refuses_is_refused_and_nothing_is_written(path, name, value, issue):
    file = write(path, COMMENTED)
    with pytest.raises(UsageError, match=re.escape(issue)):
        file.apply({name: value})
    assert path.read_text() == COMMENTED


def test_a_key_the_description_does_not_hold_is_refused(path):
    file = write(path, COMMENTED)
    with pytest.raises(UsageError, match=r"bench\.warmup: unknown key"):
        file.apply({"bench.warmup": 3})
    assert path.read_text() == COMMENTED


def test_a_table_name_is_not_a_key(path):
    with pytest.raises(UsageError, match="schedule: unknown key"):
        write(path, COMMENTED).apply({"schedule": {"max_interval_days": 3}})


def test_the_reserved_key_is_refused(path):
    with pytest.raises(UsageError, match=r"done\.auto_commit is reserved"):
        write(path, COMMENTED).apply({"done.auto_commit": True})


def test_a_file_that_does_not_parse_is_never_overwritten(path):
    broken = "# mine\nreps = = 3\n"
    file = write(path, broken)
    with pytest.raises(ConfigError, match="does not parse"):
        file.apply({"bench.reps": 3})
    assert path.read_text() == broken


def test_a_key_the_file_holds_and_this_cstudy_does_not_know_stays(path):
    file = write(path, "future_key = 1\n[bench]\nreps = 2\n")
    file.apply({"bench.reps": 3})
    assert tomllib.loads(path.read_text()) == {"future_key": 1, "bench": {"reps": 3}}


def test_fixing_one_bad_value_is_allowed_while_another_stays_bad(path):
    file = write(path, "[bench]\nreps = 0\nmemory = 3\n")
    file.apply({"bench.reps": 5})
    assert file.read().issues == ("bench.memory: expected true or false",)


def test_a_table_that_is_not_a_table_refuses_a_key_of_it(path):
    file = write(path, "bench = 3\n")
    with pytest.raises(UsageError, match="bench"):
        file.apply({"bench.reps": 5})
