import re

import pytest

from coding_study.domain import project_tests, scaffold
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Difficulty, Language, Track
from coding_study.domain.scaffold import (
    Scaffold,
    ScaffoldRequest,
    TemplateName,
    next_problem_id,
    plan_scaffold,
    render_template,
    template_directories,
)


def plan(**fields: object) -> Scaffold:
    return plan_scaffold(ScaffoldRequest(**fields), "0004")  # type: ignore[arg-type]


def test_the_first_problem_gets_id_0001():
    assert next_problem_id(()) == "0001"


def test_the_next_id_follows_the_highest():
    assert next_problem_id(("0001-two-sum", "0009-word-break", "0003-invert-binary-tree")) == "0010"


def test_directories_without_an_id_are_ignored():
    assert next_problem_id(("notes", "0002-lru-cache")) == "0003"


def test_the_first_id_applies_to_an_empty_destination():
    assert next_problem_id((), first_id=5001) == "5001"


def test_ids_above_the_first_id_keep_counting():
    assert next_problem_id(("5001-pair-sum", "5007-max-gap"), first_id=5001) == "5008"


def test_the_title_comes_from_the_slug():
    assert plan(slug="max-sub-array").title == "Max Sub Array"


def test_an_explicit_title_wins():
    assert plan(slug="lru-cache", title="LRU Cache").title == "LRU Cache"


def test_a_blank_title_is_a_usage_error():
    with pytest.raises(UsageError):
        plan(slug="two-sum", title="  ")


@pytest.mark.parametrize("slug", ["Two-Sum", "two_sum", "2sum", "two--sum", "two-", ""])
def test_invalid_slugs_are_usage_errors(slug):
    with pytest.raises(UsageError):
        plan(slug=slug)


def test_the_default_template_is_an_array_problem_in_dsa():
    scaffold = plan(slug="two-sum")
    assert (scaffold.track, scaffold.patterns) == (Track.DSA, ("arrays-hashing",))


def test_the_tree_template_defaults_to_the_trees_pattern():
    assert plan(slug="same-tree", template=TemplateName.TREE).patterns == ("trees",)


def test_the_progressive_template_defaults_to_the_practical_track():
    scaffold = plan(slug="in-memory-db", template=TemplateName.PROGRESSIVE)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


def test_the_python_project_template_defaults_to_the_practical_track():
    scaffold = plan(slug="bank-project-python", template=TemplateName.PROJECT_PYTHON)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


def test_the_typescript_project_template_defaults_to_the_practical_track():
    scaffold = plan(slug="bank-project-typescript", template=TemplateName.PROJECT_TYPESCRIPT)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


def test_the_go_project_template_defaults_to_the_practical_track():
    scaffold = plan(slug="bank-project-go", template=TemplateName.PROJECT_GO)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


@pytest.mark.parametrize("template", [TemplateName.PROJECT_JAVA, TemplateName.PROJECT_KOTLIN])
def test_the_jvm_project_templates_default_to_the_practical_track(template):
    scaffold = plan(slug=f"bank-{template}", template=template)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


def test_the_rust_project_template_defaults_to_the_practical_track():
    scaffold = plan(slug="bank-project-rust", template=TemplateName.PROJECT_RUST)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


def test_the_difficulty_defaults_to_medium():
    assert plan(slug="two-sum").difficulty is Difficulty.MEDIUM


def test_an_explicit_pattern_replaces_the_default():
    assert plan(slug="two-sum", pattern="two-pointers").patterns == ("two-pointers",)


def test_an_unknown_pattern_is_a_usage_error():
    with pytest.raises(UsageError):
        plan(slug="two-sum", pattern="hashing")


def test_dsa_without_any_pattern_is_a_usage_error():
    with pytest.raises(UsageError):
        plan(slug="in-memory-db", template=TemplateName.PROGRESSIVE, track=Track.DSA)


def test_tracks_outside_problems_are_usage_errors():
    with pytest.raises(UsageError):
        plan(slug="url-shortener", track=Track.SYSTEM_DESIGN)


def test_the_directory_name_joins_id_and_slug():
    assert plan(slug="two-sum").directory_name == "0004-two-sum"


def placeholders(**fields: object) -> dict[str, str]:
    return dict(plan(**fields).placeholders())


def test_signature_names_come_from_the_slug():
    names = placeholders(slug="max-sub-array2")
    assert (names["function_name"], names["class_name"]) == ("maxSubArray2", "MaxSubArray2")


def test_the_crate_name_is_the_slug_in_snake_case():
    assert placeholders(slug="bank-project-rust")["crate_name"] == "bank_project_rust"


def test_the_yaml_title_is_quoted():
    assert placeholders(slug="x", title='A "quoted": title')["title_yaml"] == (
        '"A \\"quoted\\": title"'
    )


def test_the_patterns_line_lists_the_patterns():
    assert placeholders(slug="x")["patterns"] == "patterns: [arrays-hashing]"


def test_rendering_replaces_placeholders():
    assert render_template("# {{title}} ({{slug}})\n", {"title": "T", "slug": "s"}) == "# T (s)\n"


def test_a_line_holding_only_an_empty_placeholder_is_dropped():
    text = "track: dsa\n{{patterns}}\nkind: function\n"
    assert render_template(text, {"patterns": ""}) == "track: dsa\nkind: function\n"


def test_blank_lines_without_placeholders_stay():
    assert render_template("a\n\nb\n", {}) == "a\n\nb\n"


def test_an_unknown_placeholder_is_an_error():
    with pytest.raises(KeyError):
        render_template("{{nope}}", {})


# the virtual clock


def test_a_template_is_its_own_directory():
    request = ScaffoldRequest("bank-project-go", TemplateName.PROJECT_GO)
    assert template_directories(request) == ("project-go",)


def test_a_go_project_on_the_virtual_clock_has_a_template_of_its_own():
    request = ScaffoldRequest("waiter-project-go", TemplateName.PROJECT_GO, virtual_clock=True)
    assert template_directories(request) == ("project-go-clock",)


def test_the_virtual_clock_variant_keeps_the_practical_track():
    scaffold = plan(slug="waiter-project-go", template=TemplateName.PROJECT_GO, virtual_clock=True)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


@pytest.mark.parametrize(
    ("template", "message"),
    [
        (TemplateName.ARRAY, "--virtual-clock applies to the project-* templates, not array"),
        (
            TemplateName.CONCURRENT,
            "--virtual-clock applies to the project-* templates, not concurrent",
        ),
        (
            TemplateName.PROJECT_JAVA,
            "--virtual-clock is not available for project-java: Java has no virtual clock",
        ),
    ],
)
def test_the_virtual_clock_is_a_usage_error_where_it_does_not_apply(template, message):
    with pytest.raises(UsageError, match=re.escape(message)):
        plan(slug="waiter", template=template, virtual_clock=True)


@pytest.mark.parametrize(
    "template",
    [
        TemplateName.PROJECT_GO,
        TemplateName.PROJECT_PYTHON,
        TemplateName.PROJECT_TYPESCRIPT,
        TemplateName.PROJECT_KOTLIN,
        TemplateName.PROJECT_RUST,
    ],
)
def test_the_virtual_clock_variant_is_a_template_of_its_own(template):
    request = ScaffoldRequest("waiter", template, virtual_clock=True)
    assert template_directories(request) == (f"{template}-clock",)


def test_the_virtual_clock_waits_for_the_runner_that_grades_it(monkeypatch):
    monkeypatch.setattr(scaffold, "GRADED_CLOCK_LANGUAGES", frozenset({Language.GO}))
    message = (
        "--virtual-clock is not available for project-python yet: "
        "the python runner does not grade the virtual clock"
    )
    with pytest.raises(UsageError, match=re.escape(message)):
        plan(slug="waiter", template=TemplateName.PROJECT_PYTHON, virtual_clock=True)


def test_the_virtual_clock_waits_for_the_generated_tests_that_run_on_it(monkeypatch):
    """The template's examples hold harness operations, which its generated tests must express."""
    monkeypatch.setattr(project_tests, "HARNESS_TEST_LANGUAGES", frozenset({Language.GO}))
    message = (
        "--virtual-clock is not available for project-python yet: "
        "cstudy does not write python tests on the virtual clock"
    )
    with pytest.raises(UsageError, match=re.escape(message)):
        plan(slug="waiter", template=TemplateName.PROJECT_PYTHON, virtual_clock=True)


# stress cases

STRESS_TEMPLATES = [
    TemplateName.PROJECT_PYTHON,
    TemplateName.PROJECT_JAVA,
    TemplateName.PROJECT_KOTLIN,
    TemplateName.PROJECT_GO,
    TemplateName.PROJECT_RUST,
]
"""The templates whose stress variant needs no virtual clock: TypeScript's stress cases run in the
async model, where only an asynchronous method can be interrupted."""
STRESS_CLOCK_TEMPLATES = [
    TemplateName.PROJECT_GO,
    TemplateName.PROJECT_PYTHON,
    TemplateName.PROJECT_TYPESCRIPT,
    TemplateName.PROJECT_KOTLIN,
    TemplateName.PROJECT_RUST,
]


@pytest.mark.parametrize("template", STRESS_TEMPLATES)
def test_a_stress_project_adds_an_overlay_to_the_project_template(template):
    request = ScaffoldRequest("tally", template, stress=True)
    assert template_directories(request) == (template, f"{template}-stress")


@pytest.mark.parametrize("template", STRESS_CLOCK_TEMPLATES)
def test_a_stress_project_on_the_virtual_clock_adds_its_overlay_to_the_clock_template(template):
    request = ScaffoldRequest("tally", template, virtual_clock=True, stress=True)
    assert template_directories(request) == (f"{template}-clock", f"{template}-clock-stress")


def test_a_stress_project_keeps_the_practical_track():
    scaffold = plan(slug="tally-project-go", template=TemplateName.PROJECT_GO, stress=True)
    assert (scaffold.track, scaffold.patterns) == (Track.PRACTICAL, ())


@pytest.mark.parametrize(
    ("template", "message"),
    [
        (TemplateName.ARRAY, "--stress applies to the project-* templates, not array"),
        (TemplateName.CONCURRENT, "--stress applies to the project-* templates, not concurrent"),
    ],
)
def test_stress_is_a_usage_error_where_it_does_not_apply(template, message):
    with pytest.raises(UsageError, match=re.escape(message)):
        plan(slug="tally", template=template, stress=True)


def test_typescript_stress_needs_the_virtual_clock():
    """Synchronous TypeScript methods are atomic on one event loop, and an asynchronous method
    needs the clock, so a stress case on the real clock could never catch a bug."""
    message = (
        "--stress is not available for project-typescript without --virtual-clock: "
        "its stress cases run in the async model, where only an asynchronous method can be "
        "interrupted, and asynchronous methods need the virtual clock"
    )
    with pytest.raises(UsageError, match=re.escape(message)):
        plan(slug="tally", template=TemplateName.PROJECT_TYPESCRIPT, stress=True)


def test_java_stress_is_a_usage_error_with_the_virtual_clock():
    message = "--virtual-clock is not available for project-java: Java has no virtual clock"
    with pytest.raises(UsageError, match=re.escape(message)):
        plan(slug="tally", template=TemplateName.PROJECT_JAVA, virtual_clock=True, stress=True)


def test_stress_does_not_lift_the_virtual_clocks_own_gate(monkeypatch):
    monkeypatch.setattr(scaffold, "GRADED_CLOCK_LANGUAGES", frozenset[Language]())
    with pytest.raises(UsageError, match="does not grade the virtual clock"):
        plan(slug="tally", template=TemplateName.PROJECT_GO, virtual_clock=True, stress=True)
