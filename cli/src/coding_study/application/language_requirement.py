"""A new attempt starts only in a workspace language (docs/specs/cli.md#the-workspaces-languages).

The other languages' folders may not exist, so `start`, `next --lang` and `mock --lang` refuse
before they write anything; `verify` skips the language instead.
"""

from coding_study.application.environment import Environment
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language


def is_workspace_language(environment: Environment, language: Language) -> bool:
    """Whether the workspace lists `language`; a workspace that chose none has all six."""
    languages = environment.workspace_languages
    return languages is None or language in languages


def not_a_workspace_language(environment: Environment, language: Language) -> str | None:
    """`rust is not one of this workspace's languages (python, go): cstudy lang add rust`; None
    when `language` is one of them."""
    if is_workspace_language(environment, language):
        return None
    listed = ", ".join(environment.workspace_languages or ())
    return f"{language} is not one of this workspace's languages ({listed}): {lang_add(language)}"


def lang_add(language: Language) -> str:
    return f"cstudy lang add {language}"


def require_workspace_language(environment: Environment, language: Language) -> None:
    """Raises UsageError (exit 3) when the workspace does not list `language`."""
    refusal = not_a_workspace_language(environment, language)
    if refusal is not None:
        raise UsageError(refusal)
