import pytest

from coding_study.domain.errors import UsageError
from coding_study.domain.preferences import (
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
}


def test_the_defaults_are_the_specs():
    assert preferences_document(Preferences()) == DEFAULT_DOCUMENT


def test_a_whole_document_parses():
    document = {"format": 1, "vim": True, "run_on_save": True, "typecheck": False}
    assert parse_preferences(document) == Preferences(vim=True, run_on_save=True, typecheck=False)


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


@pytest.mark.parametrize("value", [1, 0, "true", None, [True]])
def test_a_preference_that_is_not_a_boolean_is_refused(value):
    with pytest.raises(UsageError, match='preference "vim" must be true or false'):
        parse_preferences({"vim": value})


@pytest.mark.parametrize("value", [2, 0, True, 1.0, "1"])
def test_another_format_is_refused(value):
    with pytest.raises(UsageError, match="preferences format must be 1"):
        parse_preferences({"format": value})


@pytest.mark.parametrize("document", [[], "vim", 1, None])
def test_a_document_that_is_not_an_object_is_refused(document):
    with pytest.raises(UsageError, match="preferences must be a JSON object"):
        parse_preferences(document)
