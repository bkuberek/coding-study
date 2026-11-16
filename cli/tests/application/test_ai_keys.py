"""Keeping a provider's key (docs/specs/ai.md#keys), over `FakeCredentials`."""

import pytest

from coding_study.application.ai_keys import parse_provider, remove_key, save_key
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.errors import UsageError
from tests.fakes import FakeCredentials

SECRET = "sk-sentinel-0123456789"


@pytest.mark.parametrize("provider", list(Provider))
def test_each_provider_is_known_by_its_name(provider):
    assert parse_provider(provider.value) is provider


@pytest.mark.parametrize("name", ["antropic", "", "Anthropic", "openai:gpt", SECRET])
def test_another_name_is_no_provider_and_is_not_quoted(name):
    with pytest.raises(UsageError) as raised:
        parse_provider(name)
    assert str(raised.value) == "unknown provider; use one of anthropic, google, openai, openrouter"


def test_saving_keeps_the_key_and_says_where_the_file_is():
    credentials = FakeCredentials()
    assert save_key(credentials, Provider.ANTHROPIC, SECRET) == credentials.location
    assert credentials.keys == {Provider.ANTHROPIC: ApiKey(SECRET)}


def test_saving_again_replaces_the_key():
    credentials = FakeCredentials({Provider.OPENAI: "old-key"})
    save_key(credentials, Provider.OPENAI, SECRET)
    assert credentials.keys == {Provider.OPENAI: ApiKey(SECRET)}


@pytest.mark.parametrize("text", ["", "two words", "tab\there", "line\nbreak", " leading"])
def test_a_key_is_one_line_of_text_with_no_spaces(text):
    credentials = FakeCredentials()
    with pytest.raises(UsageError, match="a key is one line of text with no spaces"):
        save_key(credentials, Provider.ANTHROPIC, text)
    assert credentials.keys == {}


def test_a_refused_key_is_not_quoted():
    with pytest.raises(UsageError) as raised:
        save_key(FakeCredentials(), Provider.ANTHROPIC, f"{SECRET} extra")
    assert SECRET not in str(raised.value)


def test_removing_says_whether_there_was_a_key():
    credentials = FakeCredentials({Provider.OPENAI: SECRET})
    assert (
        remove_key(credentials, Provider.OPENAI),
        remove_key(credentials, Provider.OPENAI),
        credentials.keys,
    ) == (True, False, {})
