"""The range check that `start`, `test`, `submit` and `bench` make before anything builds, and the
split that `verify` makes (docs/specs/cli.md#the-selected-jdk)."""

from dataclasses import replace

import pytest

from coding_study.application.jdk_requirement import require_jdk, split_by_jdk
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.jdk import DeclaredJdk, JdkSource
from coding_study.domain.problem import Language
from tests.fakes import FakeJdk, jdk_of, make_environment
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
FIX = (
    "fix: select a JDK 21 to 26 with JAVA_HOME, or install JDK 25: "
    "https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#jdk"
)


def refusal(environment, meta, language=Language.JAVA) -> str:
    with pytest.raises(RunnerStartError) as raised:
        require_jdk(environment, meta, language)
    return str(raised.value)


@pytest.fixture
def environment(content_root):
    return make_environment(content_root)


def on(environment, jdk: FakeJdk):
    return replace(environment, jdk=jdk)


def test_a_default_problem_refuses_jdk_27(environment):
    message = refusal(on(environment, jdk_of(27)), TWO_SUM)
    assert message.splitlines()[0] == (
        "two-sum runs its java version on JDK 21 to 26; "
        "JAVA_HOME selects JDK 27, which cstudy does not support yet"
    )


def test_the_refusal_carries_the_fix_of_doctor(environment):
    assert refusal(on(environment, jdk_of(27)), TWO_SUM).splitlines()[1] == FIX


def test_a_problem_with_a_minimum_of_24_refuses_jdk_23(environment):
    meta = replace(TWO_SUM, jdk=DeclaredJdk(minimum=24))
    assert refusal(on(environment, jdk_of(23)), meta, Language.KOTLIN).splitlines()[0] == (
        "two-sum runs its kotlin version on JDK 24 to 26; JAVA_HOME selects JDK 23, "
        "which is too old"
    )


def test_a_problem_with_a_maximum_of_24_refuses_jdk_25(environment):
    meta = replace(TWO_SUM, jdk=DeclaredJdk(maximum=24))
    assert refusal(on(environment, jdk_of(25, JdkSource.PATH)), meta).splitlines()[0] == (
        "two-sum runs its java version on JDK 21 to 24; PATH selects JDK 25, "
        "which is newer than the problem supports"
    )


def test_no_jdk_refuses_a_java_problem(environment):
    message = refusal(on(environment, FakeJdk(None)), TWO_SUM)
    assert message.splitlines()[0] == (
        "two-sum runs its java version on JDK 21 to 26; no JDK was found"
    )


def test_a_java_home_without_a_jdk_refuses_a_java_problem(environment):
    jdk = FakeJdk(None, java_home_without_jdk="/opt/jdk")
    assert refusal(on(environment, jdk), TWO_SUM).splitlines()[0] == (
        "two-sum runs its java version on JDK 21 to 26; JAVA_HOME (/opt/jdk) holds no JDK"
    )


@pytest.mark.parametrize("feature", [21, 24, 26])
def test_a_jdk_in_range_passes(environment, feature):
    require_jdk(on(environment, jdk_of(feature)), TWO_SUM, Language.JAVA)


def test_a_problem_that_opts_in_to_jdk_27_passes_on_it(environment):
    meta = replace(TWO_SUM, jdk=DeclaredJdk(maximum=27))
    require_jdk(on(environment, jdk_of(27)), meta, Language.KOTLIN)


@pytest.mark.parametrize(
    "language", [Language.PYTHON, Language.TYPESCRIPT, Language.GO, Language.RUST]
)
@pytest.mark.parametrize("jdk", [jdk_of(27), FakeJdk(None)], ids=["27", "none"])
def test_the_other_languages_are_unaffected(environment, language, jdk):
    require_jdk(on(environment, jdk), TWO_SUM, language)


# verify


def test_verify_splits_off_the_jvm_languages_the_jdk_cannot_run(environment):
    meta = replace(TWO_SUM, jdk=DeclaredJdk(minimum=24))
    languages = (Language.PYTHON, Language.JAVA, Language.KOTLIN)
    split = split_by_jdk(on(environment, jdk_of(21)), meta, languages)
    assert (split.runnable, split.skipped) == ((Language.PYTHON,), (Language.JAVA, Language.KOTLIN))


def test_verify_names_the_range_and_the_jdk_of_the_skip(environment):
    meta = replace(TWO_SUM, jdk=DeclaredJdk(minimum=24))
    split = split_by_jdk(on(environment, jdk_of(21)), meta, (Language.JAVA,))
    assert split.reason == "runs on JDK 24 to 26; JAVA_HOME selects JDK 21"


def test_verify_skips_nothing_when_the_jdk_runs_the_problem(environment):
    split = split_by_jdk(on(environment, jdk_of(26)), TWO_SUM, tuple(Language))
    assert (split.runnable, split.skipped, split.reason) == (tuple(Language), (), None)


def test_verify_keeps_the_other_languages_on_a_jdk_above_the_range(environment):
    split = split_by_jdk(on(environment, jdk_of(27)), TWO_SUM, tuple(Language))
    assert Language.PYTHON in split.runnable
    assert Language.JAVA in split.skipped
