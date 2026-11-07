import pytest

from coding_study.domain.errors import UsageError
from coding_study.domain.preferences import (
    DEFAULT_PROBLEM_COLUMNS,
    Preferences,
    Theme,
    parse_preferences,
    preferences_document,
)

DEFAULT_DOCUMENT = {
    "format": 1,
    "vim": False,
    "run_on_save": False,
    "typecheck": True,
    "theme": "system",
    "code_intelligence": False,
    "autocomplete": False,
    "problem_columns": [
        "id",
        "problem",
        "difficulty",
        "pattern",
        "status",
        "due",
        "languages",
        "sets",
    ],
}


def test_the_defaults_are_the_specs():
    assert preferences_document(Preferences()) == DEFAULT_DOCUMENT


def test_a_whole_document_parses():
    document = {"format": 1, "vim": True, "run_on_save": True, "typecheck": False}
    assert parse_preferences(document) == Preferences(vim=True, run_on_save=True, typecheck=False)


def test_code_intelligence_and_autocomplete_parse_in_any_combination():
    document = {"code_intelligence": False, "autocomplete": True}
    assert parse_preferences(document) == Preferences(autocomplete=True)


def test_a_missing_key_keeps_its_default():
    assert parse_preferences({"vim": True}) == Preferences(vim=True)


def test_an_empty_document_is_the_defaults():
    assert parse_preferences({}) == Preferences()


def test_a_document_round_trips():
    preferences = Preferences(vim=True, typecheck=False)
    assert parse_preferences(preferences_document(preferences)) == preferences


def test_an_unknown_key_is_refused():
    with pytest.raises(UsageError, match='unknown preference "font"'):
        parse_preferences({"font": "serif"})


@pytest.mark.parametrize("theme", list(Theme))
def test_the_theme_is_system_light_or_dark(theme):
    assert parse_preferences({"theme": theme.value}) == Preferences(theme=theme)


@pytest.mark.parametrize("value", ["sepia", "", True, None])
def test_another_theme_is_refused(value):
    with pytest.raises(UsageError, match='preference "theme" must be system, light or dark'):
        parse_preferences({"theme": value})


def test_the_theme_is_written_by_name():
    assert preferences_document(Preferences(theme=Theme.DARK))["theme"] == "dark"


@pytest.mark.parametrize("key", ["vim", "code_intelligence", "autocomplete"])
@pytest.mark.parametrize("value", [1, 0, "true", None, [True]])
def test_a_preference_that_is_not_a_boolean_is_refused(key, value):
    with pytest.raises(UsageError, match=f'preference "{key}" must be true or false'):
        parse_preferences({key: value})


@pytest.mark.parametrize("value", [2, 0, True, 1.0, "1"])
def test_another_format_is_refused(value):
    with pytest.raises(UsageError, match="preferences format must be 1"):
        parse_preferences({"format": value})


@pytest.mark.parametrize("document", [[], "vim", 1, None])
def test_a_document_that_is_not_an_object_is_refused(document):
    with pytest.raises(UsageError, match="preferences must be a JSON object"):
        parse_preferences(document)


def test_a_document_without_columns_has_the_default_columns():
    assert parse_preferences({}).problem_columns == DEFAULT_PROBLEM_COLUMNS


def test_chosen_columns_parse():
    document = {"problem_columns": ["problem", "status", "sets"]}
    assert parse_preferences(document).problem_columns == ("problem", "status", "sets")


def test_chosen_columns_round_trip():
    preferences = Preferences(problem_columns=("problem", "status", "domain"))
    assert parse_preferences(preferences_document(preferences)) == preferences


@pytest.mark.parametrize("value", ["id", None, 3, [3], [True]])
def test_columns_that_are_not_a_list_of_names_are_refused(value):
    with pytest.raises(UsageError, match='preference "problem_columns" must be a list'):
        parse_preferences({"problem_columns": value})


def test_an_unknown_column_is_refused():
    with pytest.raises(UsageError, match='unknown column "price"'):
        parse_preferences({"problem_columns": ["problem", "status", "price"]})


@pytest.mark.parametrize("hidden", ["problem", "status"])
def test_problem_and_status_cannot_be_left_out(hidden):
    columns = [column for column in ("problem", "status", "id") if column != hidden]
    with pytest.raises(UsageError, match=f'column "{hidden}" cannot be hidden'):
        parse_preferences({"problem_columns": columns})


def test_a_column_named_twice_is_refused():
    with pytest.raises(UsageError, match='column "id" is named twice'):
        parse_preferences({"problem_columns": ["problem", "status", "id", "id"]})
