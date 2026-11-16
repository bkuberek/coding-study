from pathlib import Path

import pytest

from coding_study.adapters.toml_config import TomlConfigSource, config_path
from coding_study.domain.ai import ModelRef, Provider, Routing
from coding_study.domain.config import (
    AiSettings,
    BenchSettings,
    Config,
    DoneSettings,
    HangGuardSettings,
    NextSettings,
    ProfileSettings,
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

[profile]
job_roles = ["backend", "platform"]
domains = ["security", "identity"]

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

[ai]
enabled = true
routing = "auto"
model = "anthropic:claude-x"
fast = "openrouter:vendor/model:variant"
strong = "openai:gpt-x"
daily_token_cap = 120000
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
        profile=ProfileSettings(
            job_roles=("backend", "platform"), domains=("security", "identity")
        ),
        time_limit=TimeLimitSettings(enabled=True, value=FactorTimeLimit(3), floor_ms=50),
        hang_guard=HangGuardSettings(ms=5000),
        bench=BenchSettings(reps=9, memory=False),
        schedule=ScheduleSettings(penalize_suboptimal=False, max_interval_days=90),
        done=DoneSettings(auto_commit=True),
        study_guides=StudyGuideSettings(root="~/study-guides"),
        ai=AiSettings(
            enabled=True,
            routing=Routing.AUTO,
            model=ModelRef(Provider.ANTHROPIC, "claude-x"),
            fast=ModelRef(Provider.OPENROUTER, "vendor/model:variant"),
            strong=ModelRef(Provider.OPENAI, "gpt-x"),
            daily_token_cap=120_000,
        ),
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
        ('[profile]\njob_roles = "backend"', "profile.job_roles: expected a list of roles"),
        (
            "[profile]\njob_roles = []",
            "profile.job_roles: expected at least one role; leave the key",
        ),
        (
            '[profile]\njob_roles = ["backend", "general"]',
            'profile.job_roles: "general" always shows: list the roles you prepare for',
        ),
        ('[profile]\njob_roles = ["chef"]', 'profile.job_roles: unknown role "chef"; use one of'),
        (
            '[profile]\njob_roles = ["backend", "backend"]',
            'profile.job_roles: "backend" is listed twice',
        ),
        ("[profile]\ndomains = 3", "profile.domains: expected a list of domains"),
        ("[profile]\ndomains = []", "profile.domains: expected at least one domain; leave the key"),
        (
            '[profile]\ndomains = ["fintek"]',
            'profile.domains: unknown domain "fintek"; use one of algorithms, backend, security,',
        ),
        ("[profile]\ndomains = [1]", 'profile.domains: unknown domain "1"; use one of'),
        ("[profile]\nlanguages = []", "profile.languages: unknown key"),
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
        ('[ai]\nenabled = "yes"', "ai.enabled: expected true or false"),
        ('[ai]\nrouting = "random"', "ai.routing: expected one of fixed, auto"),
        ("[ai]\nrouting = true", "ai.routing: expected one of fixed, auto"),
        (
            '[ai]\nmodel = "claude-x"',
            "ai.model: expected provider:model, such as anthropic:<model id>",
        ),
        ("[ai]\nmodel = 5", "ai.model: expected provider:model, such as anthropic:<model id>"),
        (
            '[ai]\nfast = "gemini:x"',
            'ai.fast: unknown provider "gemini"; use one of anthropic, google, openai, openrouter',
        ),
        ('[ai]\nstrong = "openai:"', 'ai.strong: no model id after "openai:"'),
        ('[ai]\nmodel = "openai:two words"', "ai.model: a model id has no spaces"),
        ("[ai]\ndaily_token_cap = 0", "ai.daily_token_cap: expected a positive integer"),
        ("[ai]\ndaily_token_cap = -5", "ai.daily_token_cap: expected a positive integer"),
        ("[ai]\ndaily_token_cap = 1.5", "ai.daily_token_cap: expected a positive integer"),
        ("[ai]\ndaily_token_cap = true", "ai.daily_token_cap: expected a positive integer"),
        ("[ai]\nprovider = 3", "ai.provider: unknown key"),
        ("ai = true", "ai: expected a table"),
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


def test_without_a_profile_table_the_profile_holds_every_role_and_domain(tmp_path):
    profile = write_config(tmp_path, 'default_lang = "go"').load().profile
    assert profile == ProfileSettings()
    assert "general" not in profile.job_roles
    assert len(profile.domains) == 11


def test_a_profile_table_with_one_key_leaves_the_other_at_every_value(tmp_path):
    profile = write_config(tmp_path, '[profile]\ndomains = ["security"]').load().profile
    assert profile == ProfileSettings(domains=("security",))


def test_without_an_ai_table_the_preview_is_off_and_fixed_with_no_model(tmp_path):
    ai = write_config(tmp_path, "").load().ai
    assert (ai.enabled, ai.routing, ai.model, ai.fast, ai.strong) == (
        False,
        Routing.FIXED,
        None,
        None,
        None,
    )
    assert ai.daily_token_cap == 500_000


def test_an_ai_table_with_one_key_leaves_the_others_at_their_defaults(tmp_path):
    ai = write_config(tmp_path, "[ai]\nenabled = true").load().ai
    assert ai == AiSettings(enabled=True)


def test_an_unset_model_is_no_error_even_with_the_preview_on_under_auto_routing(tmp_path):
    ai = write_config(tmp_path, '[ai]\nenabled = true\nrouting = "auto"').load().ai
    assert (ai.enabled, ai.routing, ai.strong) == (True, Routing.AUTO, None)


def test_a_model_id_may_hold_colons_and_slashes(tmp_path):
    ai = write_config(tmp_path, '[ai]\nmodel = "openrouter:vendor/model:variant"').load().ai
    assert ai.model == ModelRef(Provider.OPENROUTER, "vendor/model:variant")


def test_every_ai_issue_is_collected_with_the_other_keys(tmp_path):
    text = '[ai]\nmodel = "x"\nfast = "gemini:y"\ndaily_token_cap = 0\n[bench]\nreps = 0'
    with pytest.raises(ConfigError) as raised:
        write_config(tmp_path, text).load()
    assert len(raised.value.issues) == 4
