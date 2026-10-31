import pytest

from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Difficulty, Track
from coding_study.domain.scaffold import (
    Scaffold,
    ScaffoldRequest,
    TemplateName,
    next_problem_id,
    plan_scaffold,
    render_template,
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
