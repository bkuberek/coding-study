"""`cstudy stats` against tests/stats_fixture.py, whose values are computed by hand below.

Today is 2026-10-24. In scope (ready): two-sum (arrays-hashing), lru-cache (linked-list),
invert-binary-tree (trees), url-shortener (system-design), retry-wrapper (code-review); news-feed
is a draft.

- arrays-hashing: two-sum passed in 20m (grade 2) and failed in kotlin (grade 0, 10-22); mastered
  (interval 21, last grade 2). Weakness 0.5 * 1/2 + 0.3 * 0 + 0.2 * 2/30 = 0.2633.
- linked-list: lru-cache passed in 30m with grade 1 (10-23). Weakness 0.5 + 0.3 + 0.2/30 = 0.8067.
- system-design: url-shortener passed in 45m with grade 3 today. Weakness 0.3.
- trees and code-review: untouched, weakness 0.75.
- Streak: attempts ended on 10-20, 10-22, 10-23 and 10-24, so 3 days.
- By track, dsa: 3 attempts with grades 2, 0, 1 and one of 3 problems mastered:
  0.5 * 2/3 + 0.3 * 2/3 + 0.2 * 1/30 = 0.54; solve times 20m and 30m.
- By language, python: grades 2 and 1, two-sum mastered and passed in python:
  0.5 * 1/2 + 0.3 * 2/3 + 0.2 * 1/30 = 0.4567; kotlin: one failure 2 days ago and no mastery
  (two-sum was not passed in kotlin): 0.5 + 0.3 + 0.2 * 2/30 = 0.8133.
- By difficulty, medium: lru-cache (grade 1, 30m) and url-shortener (grade 3, 45m) today:
  0.5 * 1/2 + 0.3 = 0.55, median 37m 30s; no hard content is ready.
"""

import json

import pytest
from typer.testing import CliRunner

from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import stats
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import make_environment, repository_root
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems
from tests.stats_fixture import fill_progress

runner = CliRunner()
HEADER = "GROUP           PROBLEMS  ATTEMPTED  PASSED  MASTERED  PASS RATE  SOLVE TIME  WEAKNESS"


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def environment(tmp_path, monkeypatch, problems):
    environment = make_environment(repository_root(tmp_path, problems, FIXTURE_TRACKS))
    monkeypatch.setattr(stats, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def filled(environment):
    fill_progress(environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["stats", *arguments])


def test_stats_by_pattern_match_the_hand_computed_values(filled):
    assert invoke().output.splitlines() == [
        HEADER,
        "arrays-hashing         1          1       1         1        50%     20m 00s      0.26",
        "linked-list            1          1       1         0       100%     30m 00s      0.81",
        "trees                  1          0       0         0          -           -      0.75",
        "system-design          1          1       1         0       100%     45m 00s      0.30",
        "code-review            1          0       0         0          -           -      0.75",
        "",
        "attempts  4 finished · 4 in the last 7 days · streak 3 days",
        "reviews   1 due today · 1 overdue",
        "bench     2 benched · 1 optimal · 1 near-optimal · 0 suboptimal · 0 unknown",
    ]


def test_stats_exit_0(filled):
    assert invoke().exit_code == ExitCode.SUCCESS


def test_the_group_column_fits_the_longest_name(filled):
    assert invoke("--by", "track").output.splitlines()[0] == (
        "GROUP          PROBLEMS  ATTEMPTED  PASSED  MASTERED  PASS RATE  SOLVE TIME  WEAKNESS"
    )


def test_stats_by_track(filled):
    assert invoke("--by", "track").output.splitlines()[1:4] == [
        "dsa                   3          2       2         1        67%     25m 00s      0.54",
        "system-design         1          1       1         0       100%     45m 00s      0.30",
        "code-review           1          0       0         0          -           -      0.75",
    ]


def test_stats_by_language(filled):
    assert invoke("--by", "lang").output.splitlines()[1:5] == [
        "python             3          2       2         1       100%     25m 00s      0.46",
        "typescript         3          0       0         0          -           -      0.75",
        "java               3          0       0         0          -           -      0.75",
        "kotlin             3          1       0         0         0%           -      0.81",
    ]


def test_stats_by_difficulty_leaves_out_difficulties_without_content(filled):
    assert invoke("--by", "difficulty").output.splitlines()[1:4] == [
        "easy           3          1       1         1        50%     20m 00s      0.46",
        "medium         2          2       2         0       100%     37m 30s      0.55",
        "",
    ]


def test_stats_since_narrows_the_attempt_columns(filled):
    lines = invoke("--since", "2026-10-23").output.splitlines()
    assert (lines[1], lines[7]) == (
        "arrays-hashing         1          0       0         1          -           -      0.26",
        "attempts  2 finished since 2026-10-23 · 4 in the last 7 days · streak 3 days",
    )


def test_an_invalid_since_is_a_usage_error(filled):
    assert invoke("--since", "yesterday").exit_code == ExitCode.USAGE_ERROR


def test_stats_without_progress(environment):
    assert invoke().output.splitlines()[-3:] == [
        "attempts  0 finished · 0 in the last 7 days · streak 0 days",
        "reviews   0 due today · 0 overdue",
        "bench     0 benched · 0 optimal · 0 near-optimal · 0 suboptimal · 0 unknown",
    ]


def test_stats_json(filled):
    document = json.loads(invoke("--json").output)
    assert document["groups"][0] == {
        "group": "arrays-hashing",
        "problems": 1,
        "attempted": 1,
        "passed": 1,
        "mastered": 1,
        "recent_attempts": 2,
        "recent_passed": 1,
        "pass_rate": 0.5,
        "median_solve_s": 1200,
        "weakness": 0.2633,
    }


def test_stats_json_totals(filled):
    document = json.loads(invoke("--json").output)
    del document["groups"]
    assert document == {
        "today": "2026-10-24",
        "by": "pattern",
        "since": None,
        "attempts": {"finished": 4, "last_7_days": 4, "streak_days": 3},
        "reviews": {"due_today": 1, "overdue": 1},
        "bench": {"optimal": 1, "near-optimal": 1, "suboptimal": 0, "unknown": 0},
    }


def test_command_is_registered():
    assert "stats" in {command.name for command in cli.app.registered_commands}
