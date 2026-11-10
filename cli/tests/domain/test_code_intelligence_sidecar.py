"""The servers of a service project, which run in its sidecar on the project's own dependencies
(docs/specs/service-projects.md#language-servers)."""

from dataclasses import replace

import pytest

from coding_study.adapters.problem_documents import meta_from_document
from coding_study.domain.cases import JsonValue
from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    GOPLS,
    TYPESCRIPT_LANGUAGE_SERVER,
    NoCodeIntelligence,
    no_code_intelligence,
    sidecar_server,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.service_project import service_of
from tests.service_problems import meta_document

FOLDER = "/work/projects/rooms"


def typescript_options() -> dict[str, JsonValue]:
    return sidecar_server(TYPESCRIPT_LANGUAGE_SERVER, FOLDER).initialization_options("/work")


def test_typescript_in_a_sidecar_runs_the_projects_own_compiler():
    assert typescript_options()["tsserver"] == {"path": f"{FOLDER}/node_modules/typescript/lib"}


def test_typescript_in_a_sidecar_keeps_the_catalogs_other_options():
    options = typescript_options()

    assert (options["disableAutomaticTypingAcquisition"], options["preferences"]) == (
        True,
        {"includeCompletionsForModuleExports": False},
    )


def test_typescript_in_a_sidecar_needs_nothing_of_the_workspaces_practice_project():
    assert sidecar_server(TYPESCRIPT_LANGUAGE_SERVER, FOLDER).requirement is None


def test_typescript_in_a_sidecar_runs_the_same_script():
    assert sidecar_server(TYPESCRIPT_LANGUAGE_SERVER, FOLDER).script == (
        TYPESCRIPT_LANGUAGE_SERVER.script
    )


def test_basedpyright_in_a_sidecar_is_the_catalogs_own():
    """The project's `[tool.pyright]` names its `.venv`, which the server reads without Python."""
    assert sidecar_server(BASEDPYRIGHT, FOLDER) is BASEDPYRIGHT


def service_meta(language: str) -> ProblemMeta:
    return meta_from_document({**meta_document(), "languages": [language]}, "meta.yaml")


@pytest.mark.parametrize("language", [Language.TYPESCRIPT, Language.PYTHON])
def test_a_service_project_in_typescript_or_python_has_code_intelligence(language):
    assert no_code_intelligence(service_meta(language.value), language) is None


def test_a_service_project_in_another_language_has_none_yet():
    meta = service_meta("go")

    assert no_code_intelligence(meta, Language.GO) is NoCodeIntelligence.SERVICE_PROJECT


def test_the_service_meta_of_these_tests_is_a_service_project():
    assert service_of(service_meta("go")) is not None


def test_a_problem_that_is_no_service_project_has_its_servers_say():
    meta = replace(service_meta("go"), project=None)

    assert no_code_intelligence(meta, Language.GO) is None


def test_gopls_has_no_sidecar_variant_to_offer():
    with pytest.raises(ValueError, match="gopls runs in no sidecar"):
        sidecar_server(GOPLS, FOLDER)
