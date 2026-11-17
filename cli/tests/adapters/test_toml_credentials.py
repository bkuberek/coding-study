"""`credentials.toml` (docs/specs/ai.md#keys): strict loading, whole and atomic rewrites with mode
0600, the file gone with its last key, and the refusal inside the workspace."""

import os
import stat
import tomllib
from pathlib import Path

import pytest

from coding_study.adapters.toml_credentials import (
    TomlCredentials,
    credentials_path,
    git_tree_of,
    open_credentials,
)
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.errors import ConfigError, UsageError

SECRET = "sk-sentinel-0123456789"
OTHER_SECRET = "or-sentinel-9876543210"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    return root


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "config" / "coding-study" / "credentials.toml"


@pytest.fixture
def credentials(path: Path, workspace: Path) -> TomlCredentials:
    return TomlCredentials(path, workspace)


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def written(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# where it is


def test_the_file_is_beside_the_config_file_the_environment_names(tmp_path, workspace):
    config = tmp_path / "elsewhere" / "settings.toml"
    found = open_credentials({"CSTUDY_CONFIG": str(config)}, tmp_path, workspace)
    assert found.location == str(tmp_path / "elsewhere" / "credentials.toml")


def test_the_file_is_under_the_xdg_config_home(tmp_path, workspace):
    found = open_credentials({"XDG_CONFIG_HOME": str(tmp_path / "xdg")}, tmp_path, workspace)
    assert found.location == str(tmp_path / "xdg" / "coding-study" / "credentials.toml")


def test_the_file_is_under_the_home_directory_by_default(tmp_path, workspace):
    found = open_credentials({}, tmp_path, workspace)
    assert found.location == str(tmp_path / ".config" / "coding-study" / "credentials.toml")


def test_the_path_beside_a_config_file_is_credentials_toml():
    assert credentials_path(Path("/a/b/config.toml")) == Path("/a/b/credentials.toml")


# reading


def test_a_missing_file_has_no_keys_and_no_issue(credentials):
    assert (credentials.keys_set(), credentials.key(Provider.OPENAI), credentials.issue()) == (
        frozenset(),
        None,
        None,
    )


def test_a_file_you_made_is_read_whatever_its_mode(credentials, path):
    written(path, f'[openai]\napi_key = "{SECRET}"\n')
    path.chmod(0o644)
    assert (credentials.keys_set(), credentials.issue()) == (frozenset({Provider.OPENAI}), None)


def test_a_key_reads_back_as_the_key_that_was_saved(credentials):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert credentials.key(Provider.ANTHROPIC) == ApiKey(SECRET)


@pytest.mark.parametrize("secret", ['a"b\\c', "café-\U0001f511", "x" * 5000, "a'b#c=d"])
def test_a_key_with_quotes_backslashes_or_non_ascii_survives_the_file(credentials, path, secret):
    credentials.save_key(Provider.GOOGLE, ApiKey(secret))
    assert tomllib.loads(path.read_text(encoding="utf-8"))["google"]["api_key"] == secret
    assert credentials.key(Provider.GOOGLE) == ApiKey(secret)


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ('[antropic]\napi_key = "x"\n', 'unknown provider "antropic"'),
        ('[anthropic]\nsecret = "x"\n', 'anthropic: unknown key "secret"'),
        ('[anthropic]\napi_key = ""\n', "anthropic: api_key must be a non-empty string"),
        ("[anthropic]\napi_key = 12\n", "anthropic: api_key must be a non-empty string"),
        ("[anthropic]\n", "anthropic: api_key must be a non-empty string"),
        ('anthropic = "x"\n', "anthropic: expected a table"),
        (
            '[anthropic]\napi_key = "two words"\n',
            "anthropic: api_key must be one line of text with no spaces",
        ),
        ("[anthropic\n", "it is not valid TOML"),
    ],
)
def test_a_file_that_does_not_load_names_the_problem(credentials, path, text, problem):
    written(path, text)
    assert credentials.issue() == f"credentials.toml: {problem}"
    with pytest.raises(ConfigError) as raised:
        credentials.keys_set()
    assert str(raised.value) == f"{path}: {problem}"


def test_a_file_that_is_not_text_does_not_load(credentials, path):
    path.parent.mkdir(parents=True)
    path.write_bytes(b"\xff\xfe\x00")
    assert credentials.issue() == "credentials.toml: it cannot be read"


def test_no_problem_text_holds_a_key(credentials, path):
    written(path, f'[anthropic]\napi_key = "{SECRET} two"\n[openai]\napi_key = "{OTHER_SECRET}"\n')
    assert SECRET not in (credentials.issue() or "")
    with pytest.raises(ConfigError) as raised:
        credentials.key(Provider.OPENAI)
    assert SECRET not in str(raised.value)
    assert OTHER_SECRET not in str(raised.value)


# writing


def test_a_saved_key_is_in_a_file_of_mode_0600_in_a_directory_of_mode_0700(credentials, path):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert (mode(path), mode(path.parent)) == (0o600, 0o700)


def test_an_existing_directory_keeps_its_mode(credentials, path):
    path.parent.mkdir(parents=True)
    path.parent.chmod(0o755)
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert mode(path.parent) == 0o755


def test_a_file_of_mode_0644_is_rewritten_as_0600(credentials, path):
    written(path, f'[openai]\napi_key = "{SECRET}"\n')
    path.chmod(0o644)
    credentials.save_key(Provider.OPENAI, ApiKey(OTHER_SECRET))
    assert mode(path) == 0o600


def test_the_file_starts_with_one_comment_line_that_points_at_the_docs(credentials, path):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == [
        "# Your AI provider keys. cstudy rewrites this file whole: comments you add do not "
        "survive (cstudy docs ai).",
        "",
    ]
    assert lines[2] == "[anthropic]"


def test_the_providers_are_listed_in_order(credentials, path):
    for provider in (Provider.OPENROUTER, Provider.ANTHROPIC, Provider.OPENAI):
        credentials.save_key(provider, ApiKey(f"key-{provider}"))
    headings = [
        line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("[")
    ]
    assert headings == ["[anthropic]", "[openai]", "[openrouter]"]


def test_saving_a_key_keeps_the_others(credentials):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    credentials.save_key(Provider.OPENAI, ApiKey(OTHER_SECRET))
    assert credentials.keys_set() == {Provider.ANTHROPIC, Provider.OPENAI}


def test_saving_a_key_again_replaces_it(credentials):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    credentials.save_key(Provider.ANTHROPIC, ApiKey(OTHER_SECRET))
    assert credentials.key(Provider.ANTHROPIC) == ApiKey(OTHER_SECRET)


def test_a_write_leaves_no_temporary_file(credentials, path):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert [entry.name for entry in path.parent.iterdir()] == ["credentials.toml"]


def test_comments_added_by_hand_do_not_survive_a_write(credentials, path):
    written(path, f'# mine\n[openai]\napi_key = "{SECRET}"\n')
    credentials.save_key(Provider.ANTHROPIC, ApiKey(OTHER_SECRET))
    assert "# mine" not in path.read_text(encoding="utf-8")


def test_a_file_that_does_not_load_is_not_written(credentials, path):
    broken = '[antropic]\napi_key = "x"\n'
    written(path, broken)
    with pytest.raises(ConfigError):
        credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert path.read_text(encoding="utf-8") == broken


def test_a_write_that_fails_leaves_the_file_as_it_was(credentials, path, monkeypatch):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    before = path.read_bytes()

    def failing(*arguments, **keywords):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "fsync", failing)
    with pytest.raises(ConfigError, match="cannot be written: No space left on device") as raised:
        credentials.save_key(Provider.OPENAI, ApiKey(OTHER_SECRET))
    assert (path.read_bytes(), [entry.name for entry in path.parent.iterdir()]) == (
        before,
        ["credentials.toml"],
    )
    assert OTHER_SECRET not in str(raised.value)


@pytest.mark.skipif(os.geteuid() == 0, reason="root writes anywhere")
def test_a_directory_that_cannot_be_made_is_a_config_error(tmp_path, workspace):
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)
    credentials = TomlCredentials(locked / "sub" / "credentials.toml", workspace)
    with pytest.raises(ConfigError, match="cannot be written: Permission denied"):
        credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert not (locked / "sub").exists()


def test_a_path_through_a_file_is_a_file_that_cannot_be_read(tmp_path, workspace):
    blocker = written(tmp_path / "blocker", "a file")
    credentials = TomlCredentials(blocker / "credentials.toml", workspace)
    assert credentials.issue() == "credentials.toml: it cannot be read"


def test_a_link_keeps_pointing_where_it_did(tmp_path, workspace):
    real = written(tmp_path / "dotfiles" / "credentials.toml", f'[openai]\napi_key = "{SECRET}"\n')
    link = tmp_path / "config" / "credentials.toml"
    link.parent.mkdir()
    link.symlink_to(real)
    TomlCredentials(link, workspace).save_key(Provider.ANTHROPIC, ApiKey(OTHER_SECRET))
    assert (link.is_symlink(), "[anthropic]" in real.read_text(encoding="utf-8")) == (True, True)


# removing


def test_removing_a_key_keeps_the_others(credentials):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    credentials.save_key(Provider.OPENAI, ApiKey(OTHER_SECRET))
    assert (credentials.remove_key(Provider.ANTHROPIC), credentials.keys_set()) == (
        True,
        frozenset({Provider.OPENAI}),
    )


def test_the_file_goes_with_its_last_key(credentials, path):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    assert (credentials.remove_key(Provider.ANTHROPIC), path.exists()) == (True, False)


def test_removing_a_key_that_is_not_there_changes_nothing(credentials, path):
    credentials.save_key(Provider.ANTHROPIC, ApiKey(SECRET))
    before = path.read_bytes()
    assert (credentials.remove_key(Provider.OPENAI), path.read_bytes()) == (False, before)


def test_removing_from_a_missing_file_creates_nothing(credentials, path):
    assert (credentials.remove_key(Provider.OPENAI), path.parent.exists()) == (False, False)


def test_removing_from_a_file_that_does_not_load_fails_and_keeps_it(credentials, path):
    broken = "[anthropic\n"
    written(path, broken)
    with pytest.raises(ConfigError):
        credentials.remove_key(Provider.ANTHROPIC)
    assert path.read_text(encoding="utf-8") == broken


# inside the workspace


def inside(workspace: Path) -> TomlCredentials:
    return TomlCredentials(workspace / "config" / "credentials.toml", workspace)


def test_a_file_inside_the_workspace_is_an_issue_with_the_spec_text(workspace):
    where = workspace / "config" / "credentials.toml"
    assert inside(workspace).issue() == (
        f"credentials.toml would be inside this workspace ({where}): keys never go in a "
        "workspace; point CSTUDY_CONFIG at a config.toml outside it"
    )


def test_a_file_inside_the_workspace_is_neither_read_nor_written(workspace):
    credentials = inside(workspace)
    file = written(workspace / "config" / "credentials.toml", f'[openai]\napi_key = "{SECRET}"\n')
    before = file.read_bytes()
    for action in (
        credentials.keys_set,
        lambda: credentials.key(Provider.OPENAI),
        lambda: credentials.save_key(Provider.ANTHROPIC, ApiKey(OTHER_SECRET)),
        lambda: credentials.remove_key(Provider.OPENAI),
    ):
        with pytest.raises(UsageError, match="would be inside this workspace"):
            action()
    assert file.read_bytes() == before


def test_a_file_that_leads_into_the_workspace_by_a_link_is_inside_it(tmp_path, workspace):
    (tmp_path / "alias").symlink_to(workspace, target_is_directory=True)
    credentials = TomlCredentials(tmp_path / "alias" / "credentials.toml", workspace)
    assert "would be inside this workspace" in (credentials.issue() or "")


def test_a_file_beside_the_workspace_is_not_inside_it(tmp_path, workspace):
    credentials = TomlCredentials(tmp_path / "ws-config" / "credentials.toml", workspace)
    assert credentials.issue() is None


# the Git working tree, for the doctor


def test_a_file_under_a_git_working_tree_names_its_root(tmp_path):
    (tmp_path / "repository" / ".git").mkdir(parents=True)
    file = tmp_path / "repository" / "config" / "credentials.toml"
    assert git_tree_of(file) == (tmp_path / "repository").resolve()


def test_the_git_entry_of_a_worktree_is_a_file(tmp_path):
    written(tmp_path / "worktree" / ".git", "gitdir: /elsewhere\n")
    assert (
        git_tree_of(tmp_path / "worktree" / "a" / "credentials.toml")
        == (tmp_path / "worktree").resolve()
    )


def test_the_nearest_git_working_tree_wins(tmp_path):
    (tmp_path / "outer" / ".git").mkdir(parents=True)
    (tmp_path / "outer" / "inner" / ".git").mkdir(parents=True)
    assert (
        git_tree_of(tmp_path / "outer" / "inner" / "credentials.toml")
        == (tmp_path / "outer" / "inner").resolve()
    )


def test_a_file_outside_any_git_working_tree_has_none(tmp_path):
    assert git_tree_of(tmp_path / "config" / "credentials.toml") is None
