from pathlib import Path

import pytest

from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.domain.config import (
    BenchSettings,
    Config,
    DoneSettings,
    HangGuardSettings,
    NextSettings,
    ScheduleSettings,
    StudyGuideSettings,
    TimeLimitSettings,
)
from coding_study.domain.errors import ConfigError
from coding_study.domain.problem import Language, Track
from coding_study.domain.scheduling import ReviewIntervals
from coding_study.domain.time_limits import FactorTimeLimit

HOME = Path("/home/user")
DEFAULT_PATH = HOME / ".config/coding-study/config.toml"

FULL_CONFIG = """
default_lang = "kotlin"
open_on_start = false
progress_db = "data/progress.db"

[next]
tracks = ["dsa", "system-design"]

[time_limit]
enabled = true
value = "3x"
floor_ms = 50

[hang_guard]
ms = 5000

[bench]
reps = 9
memory = false

[schedule]
penalize_suboptimal = false
max_interval_days = 90

[done]
auto_commit = true

[study_guides]
root = "~/study-guides"
"""


def test_cs_config_beats_xdg_config_home():
    environ = {"CSTUDY_CONFIG": "/etc/cs.toml", "XDG_CONFIG_HOME": "/xdg"}
    assert config_path(environ, HOME) == Path("/etc/cs.toml")


def test_xdg_config_home_beats_home_default():
    assert config_path({"XDG_CONFIG_HOME": "/xdg"}, HOME) == Path("/xdg/coding-study/config.toml")


def test_default_path_is_under_home_config():
    assert config_path({}, HOME) == DEFAULT_PATH


@pytest.mark.parametrize(
    "environ",
    [{"CSTUDY_CONFIG": ""}, {"XDG_CONFIG_HOME": ""}, {"XDG_CONFIG_HOME": "relative/dir"}],
    ids=["empty CSTUDY_CONFIG", "empty XDG_CONFIG_HOME", "relative XDG_CONFIG_HOME"],
)
def test_empty_or_relative_variables_are_ignored(environ):
    assert config_path(environ, HOME) == DEFAULT_PATH


def write_config(tmp_path: Path, text: str) -> TomlConfigSource:
    path = tmp_path / "config.toml"
    path.write_text(text)
    return TomlConfigSource(path)


def test_missing_file_does_not_exist(tmp_path):
    assert TomlConfigSource(tmp_path / "missing.toml").exists() is False


def test_missing_file_loads_built_in_defaults(tmp_path):
    assert TomlConfigSource(tmp_path / "missing.toml").load() == Config()


def test_location_is_the_file_path(tmp_path):
    assert TomlConfigSource(tmp_path / "config.toml").location == str(tmp_path / "config.toml")


def test_empty_file_loads_built_in_defaults(tmp_path):
    assert write_config(tmp_path, "").load() == Config()


def test_every_key_is_read(tmp_path):
    assert write_config(tmp_path, FULL_CONFIG).load() == Config(
        default_lang=Language.KOTLIN,
        open_on_start=False,
        progress_db="data/progress.db",
        next=NextSettings(tracks=(Track.DSA, Track.SYSTEM_DESIGN)),
        time_limit=TimeLimitSettings(enabled=True, value=FactorTimeLimit(3), floor_ms=50),
        hang_guard=HangGuardSettings(ms=5000),
        bench=BenchSettings(reps=9, memory=False),
        schedule=ScheduleSettings(penalize_suboptimal=False, max_interval_days=90),
        done=DoneSettings(auto_commit=True),
        study_guides=StudyGuideSettings(root="~/study-guides"),
    )


@pytest.mark.parametrize(
    ("text", "issue"),
    [
        (
            'default_lang = "scala"',
            "default_lang: expected one of python, typescript, java, kotlin, go, rust",
        ),
        ('open_on_start = "yes"', "open_on_start: expected true or false"),
        ("progress_db = 5", "progress_db: expected a non-empty string"),
        ('[next]\ntracks = "dsa"', "next.tracks: expected a list of track ids"),
        ('[next]\ntracks = ["chess"]', 'next.tracks: unknown track "chess"'),
        ('[time_limit]\nvalue = "fast"', 'time_limit.value: invalid time limit "fast"'),
        ("[time_limit]\nfloor_ms = 0", "time_limit.floor_ms: expected a positive integer"),
        ("[hang_guard]\nms = -1", "hang_guard.ms: expected a positive integer"),
        ("[bench]\nreps = true", "bench.reps: expected a positive integer"),
        ("[schedule]\nmax_interval_days = 1.5", "schedule.max_interval_days: expected a positive"),
        (
            "[schedule]\nagain_interval_days = 0",
            "schedule.again_interval_days: expected a positive",
        ),
        (
            "[schedule]\nhard_first_interval_days = -2",
            "schedule.hard_first_interval_days: expected",
        ),
        ('[schedule]\nok_first_interval_days = "3"', "schedule.ok_first_interval_days: expected"),
        ("[schedule]\nok_second_interval_days = 1.5", "schedule.ok_second_interval_days: expected"),
        (
            "[schedule]\neasy_first_interval_days = true",
            "schedule.easy_first_interval_days: expect",
        ),
        ("[schedule]\neasy_second_interval_days = 0", "schedule.easy_second_interval_days: expect"),
        ("[schedule]\nmastered_interval_days = 0", "schedule.mastered_interval_days: expected"),
        (
            "[schedule]\nmastered_interval_days = 200",
            "schedule.mastered_interval_days: 200 is above schedule.max_interval_days (180)",
        ),
        ("[done]\nauto_commit = 1", "done.auto_commit: expected true or false"),
        (
            '[study_guides]\nroot = "guides"',
            'study_guides.root: expected an absolute path or one starting with "~/"',
        ),
        ('[study_guides]\nroot = ""', "study_guides.root: expected an absolute path"),
        ('colour = "auto"', "colour: unknown key"),
        ("[bench]\nwarmup = 3", "bench.warmup: unknown key"),
        ("bench = 3", "bench: expected a table"),
    ],
)
def test_invalid_values_are_reported_by_key(tmp_path, text, issue):
    with pytest.raises(ConfigError) as raised:
        write_config(tmp_path, text).load()
    [reported] = raised.value.issues
    assert reported.startswith(issue)


def test_every_issue_is_collected(tmp_path):
    with pytest.raises(ConfigError) as raised:
        write_config(tmp_path, 'default_lang = "scala"\nopen_on_start = 1\n').load()
    assert len(raised.value.issues) == 2


def test_invalid_toml_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="line 1"):
        write_config(tmp_path, "default_lang = \n").load()


def test_config_error_names_the_file(tmp_path):
    source = write_config(tmp_path, 'default_lang = "scala"')
    with pytest.raises(ConfigError) as raised:
        source.load()
    assert raised.value.source == source.location


def test_the_review_intervals_are_read_from_the_schedule_table(tmp_path):
    text = """
[schedule]
again_interval_days = 2
hard_first_interval_days = 3
ok_first_interval_days = 4
ok_second_interval_days = 8
easy_first_interval_days = 6
easy_second_interval_days = 14
mastered_interval_days = 30
"""
    assert write_config(tmp_path, text).load().schedule == ScheduleSettings(
        intervals=ReviewIntervals(
            again=2, hard_first=3, ok_first=4, ok_second=8, easy_first=6, easy_second=14
        ),
        mastered_interval_days=30,
    )


def test_a_low_maximum_with_the_default_mastered_threshold_still_loads(tmp_path):
    config = write_config(tmp_path, "[schedule]\nmax_interval_days = 14\n").load()
    assert config.schedule.max_interval_days == 14


def test_a_mastered_threshold_equal_to_the_maximum_is_reachable(tmp_path):
    text = "[schedule]\nmax_interval_days = 30\nmastered_interval_days = 30\n"
    assert write_config(tmp_path, text).load().schedule.mastered_interval_days == 30
