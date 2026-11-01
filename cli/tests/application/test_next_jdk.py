"""`cstudy next` never picks a problem the selected JDK cannot run in the language it would start
it in, and says why when that leaves nothing (docs/specs/cli.md#cstudy-next)."""

from pathlib import Path

import pytest

from coding_study.application.next_problem import (
    NextRequest,
    NothingToPick,
    next_problem,
    recommend,
)
from coding_study.domain.config import Config
from coding_study.domain.items import EntryKind
from coding_study.domain.problem import Language, Track
from tests.fakes import FakeJdk, declare_jdk, jdk_of, make_environment
from tests.fakes import repository_root as copy_repository
from tests.helpers import FIRST_CATALOG, FIXTURE_TRACKS, copy_catalog_problems

JVM_PROJECTS = Path(__file__).resolve().parents[1] / "fixtures" / "jvm-projects" / "problems"
JAVA = NextRequest(language=Language.JAVA)
NOTHING_ON_27 = "JDK 27 (JAVA_HOME) cannot run java problems; cstudy supports JDK 21 to 26"


@pytest.fixture
def problems(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


def environment_on(tmp_path: Path, problems: Path, jdk: FakeJdk, **parts: object):
    return make_environment(copy_repository(tmp_path, problems), jdk=jdk, **parts)


def picked(environment, request: NextRequest | None = None) -> str | None:
    result = next_problem(environment, request or NextRequest())
    return result.candidate.slug if result is not None else None


def test_a_jdk_in_range_changes_no_pick(tmp_path, problems):
    environment = environment_on(tmp_path, problems, jdk_of(26))
    assert picked(environment, JAVA) == "two-sum"


@pytest.mark.parametrize("jdk", [jdk_of(27), FakeJdk(None)], ids=["JDK 27", "no JDK"])
def test_the_default_language_python_needs_no_jdk(tmp_path, problems, jdk):
    assert picked(environment_on(tmp_path, problems, jdk)) == "two-sum"


@pytest.mark.parametrize("jdk", [jdk_of(27), jdk_of(17), FakeJdk(None)])
def test_a_java_pick_needs_a_jdk_that_runs_it(tmp_path, problems, jdk):
    assert picked(environment_on(tmp_path, problems, jdk), JAVA) is None


def test_the_configured_default_language_counts_as_the_language_to_start_in(tmp_path, problems):
    config = Config(default_lang=Language.KOTLIN)
    environment = environment_on(tmp_path, problems, jdk_of(27), config=config)
    assert picked(environment) is None


def test_a_problem_whose_range_excludes_the_jdk_gives_way_to_the_next_one(tmp_path, problems):
    root = copy_repository(tmp_path, problems)
    declare_jdk(root, "0001-two-sum", "{min: 24}")
    environment = make_environment(root, jdk=jdk_of(23))
    assert picked(environment, JAVA) == "lru-cache"


def test_a_problem_whose_range_holds_the_jdk_is_picked(tmp_path, problems):
    root = copy_repository(tmp_path, problems)
    declare_jdk(root, "0001-two-sum", "{min: 24}")
    assert picked(make_environment(root, jdk=jdk_of(24)), JAVA) == "two-sum"


def test_a_problem_that_opts_in_to_the_jdk_is_the_only_pick_on_it(tmp_path, problems):
    root = copy_repository(tmp_path, problems)
    declare_jdk(root, "0003-invert-binary-tree", "{max: 27}")
    assert picked(make_environment(root, jdk=jdk_of(27)), JAVA) == "invert-binary-tree"


def test_items_stay_in_scope_whatever_the_jdk(tmp_path, problems):
    environment = make_environment(
        copy_repository(tmp_path, problems, FIXTURE_TRACKS), jdk=FakeJdk(None)
    )
    request = NextRequest(tracks=(Track.SYSTEM_DESIGN,), language=Language.JAVA)
    result = recommend(environment, request)
    assert not isinstance(result, NothingToPick)
    assert result.kind is EntryKind.ITEM


# the message


def test_nothing_to_pick_says_which_jdk_ran_out_of_problems(tmp_path, problems):
    result = recommend(environment_on(tmp_path, problems, jdk_of(27)), JAVA)
    assert result == NothingToPick(NOTHING_ON_27)


def test_no_jdk_is_named(tmp_path, problems):
    result = recommend(environment_on(tmp_path, problems, FakeJdk(None)), JAVA)
    assert result == NothingToPick(
        "no JDK was found, so java problems cannot run; cstudy supports JDK 21 to 26"
    )


def test_a_java_home_without_a_jdk_is_named(tmp_path, problems):
    jdk = FakeJdk(None, java_home_without_jdk="/opt/jdk")
    result = recommend(environment_on(tmp_path, problems, jdk), JAVA)
    assert result == NothingToPick(
        "JAVA_HOME (/opt/jdk) holds no JDK, so java problems cannot run; "
        "cstudy supports JDK 21 to 26"
    )


def test_an_empty_scope_is_not_blamed_on_the_jdk(tmp_path, problems):
    environment = environment_on(tmp_path, problems, jdk_of(27))
    result = recommend(environment, NextRequest(tracks=(Track.PRACTICAL,), language=Language.JAVA))
    assert result == NothingToPick(None)


def test_a_jdk_that_took_nothing_out_is_not_blamed(tmp_path, problems):
    environment = environment_on(tmp_path, problems, jdk_of(26))
    result = recommend(environment, NextRequest(tracks=(Track.PRACTICAL,), language=Language.JAVA))
    assert result == NothingToPick(None)


def test_a_pick_is_a_recommendation(tmp_path, problems):
    result = recommend(environment_on(tmp_path, problems, jdk_of(27)), NextRequest())
    assert not isinstance(result, NothingToPick)
    assert result.title == "Two Sum"


# project problems start in their own language


def ready_java_project(tmp_path: Path, jdk: FakeJdk):
    """The Java project fixture, whose content is ready for `next`."""
    root = copy_repository(tmp_path, JVM_PROJECTS)
    meta = root / "problems" / "0001-bank-project-java" / "meta.yaml"
    meta.write_text(meta.read_text().replace("status: draft", "status: ready"))
    return make_environment(root, jdk=jdk)


def test_a_java_project_is_not_picked_on_a_jdk_that_cannot_run_it(tmp_path):
    environment = ready_java_project(tmp_path, jdk_of(27))
    request = NextRequest(tracks=(Track.PRACTICAL,))
    assert recommend(environment, request) == NothingToPick(
        "JDK 27 (JAVA_HOME) cannot run java problems; cstudy supports JDK 21 to 26"
    )


def test_a_java_project_is_picked_on_a_jdk_that_runs_it(tmp_path):
    environment = ready_java_project(tmp_path, jdk_of(21))
    result = recommend(environment, NextRequest(tracks=(Track.PRACTICAL,)))
    assert not isinstance(result, NothingToPick)
    assert result.language is Language.JAVA
