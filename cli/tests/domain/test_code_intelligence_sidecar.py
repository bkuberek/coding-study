"""The servers of a service project, which run in its sidecar on the project's own dependencies
(docs/specs/service-projects.md#language-servers)."""

from dataclasses import replace

import pytest

from coding_study.adapters.problem_documents import meta_from_document
from coding_study.domain.cases import JsonValue
from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    GOPLS,
    JDTLS,
    KOTLIN_LSP,
    RUST_ANALYZER,
    TYPESCRIPT_LANGUAGE_SERVER,
    Launch,
    NoCodeIntelligence,
    cache_install,
    cache_install_of,
    no_code_intelligence,
    sidecar_image,
    sidecar_server,
    sidecar_toolchain,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.sandbox import NODE_IMAGE, SidecarToolchain
from coding_study.domain.service_project import ServiceProject, service_of
from tests.service_problems import (
    GO_IMAGE,
    GRADLE_IMAGE,
    go_meta_document,
    java_meta_document,
    meta_document,
)

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


@pytest.mark.parametrize(
    "language", [Language.TYPESCRIPT, Language.PYTHON, Language.JAVA, Language.GO]
)
def test_a_service_project_with_a_sidecar_server_has_code_intelligence(language):
    assert no_code_intelligence(service_meta(language.value), language) is None


def test_a_service_project_in_another_language_has_none_yet():
    meta = service_meta("kotlin")

    assert no_code_intelligence(meta, Language.KOTLIN) is NoCodeIntelligence.SERVICE_PROJECT


def test_the_service_meta_of_these_tests_is_a_service_project():
    assert service_of(service_meta("kotlin")) is not None


def test_a_problem_that_is_no_service_project_has_its_servers_say():
    meta = replace(service_meta("kotlin"), project=None)

    assert no_code_intelligence(meta, Language.KOTLIN) is None


@pytest.mark.parametrize("server", [KOTLIN_LSP, RUST_ANALYZER])
def test_a_server_of_no_sidecar_has_no_sidecar_variant_to_offer(server):
    with pytest.raises(ValueError, match=f"{server.name} runs in no sidecar"):
        sidecar_server(server, FOLDER)


def test_a_go_service_project_has_code_intelligence():
    assert no_code_intelligence(service_meta("go"), Language.GO) is None


def test_gopls_runs_on_the_projects_own_image_whose_go_loads_the_project():
    assert sidecar_image(GOPLS, GO_IMAGE) == GO_IMAGE


def test_gopls_in_a_sidecar_is_the_one_the_install_built_into_the_install_cache():
    launch = Launch("/work/.cs/lsp", platform="linux")

    assert sidecar_server(GOPLS, FOLDER).command(launch) == ("/cache/gopls/0.24.0/gopls",)


def test_only_a_server_that_go_builds_is_built_into_an_install_cache():
    assert (cache_install(JDTLS), cache_install(BASEDPYRIGHT)) == (None, None)


def test_the_install_builds_the_newest_gopls_the_catalog_pins():
    """Every Go service project's image is Go 1.27, which builds the newest."""
    install = cache_install(GOPLS)

    assert install is not None
    assert (install.version, install.command[-1]) == (
        "0.24.0",
        "golang.org/x/tools/gopls@v0.24.0",
    )


def test_a_go_service_projects_install_builds_gopls():
    install = cache_install_of(meta_from_document(go_meta_document(), "meta.yaml"))

    assert install is not None
    assert install.name == "gopls"


def test_a_java_service_projects_install_builds_no_server():
    assert cache_install_of(meta_from_document(java_meta_document(), "meta.yaml")) is None


def go_toolchain() -> SidecarToolchain:
    service = service_of(meta_from_document(go_meta_document(), "meta.yaml"))
    assert service is not None
    toolchain = sidecar_toolchain(GOPLS, service, DATA, CACHE)
    assert toolchain is not None
    return toolchain


def test_gopls_loads_the_project_with_the_projects_own_go_variables():
    """The module cache read-only in the install cache, no proxy and no module file changed; the
    build cache and gopls's file cache in the data folder, since the install cache is read-only
    there, and no temporary folder in it either."""
    assert go_toolchain().environment == {
        "GOPROXY": "off",
        "GOFLAGS": "-mod=readonly",
        "GOMODCACHE": "/cache/go/mod",
        "GOWORK": "off",
        "CGO_ENABLED": "0",
        "GOCACHE": f"{DATA}/go-build",
        "XDG_CACHE_HOME": f"{DATA}/cache",
    }


def test_gopls_leaves_the_project_folder_read_only():
    assert not go_toolchain().writable_project


def test_gopls_has_room_for_the_go_list_processes_it_starts():
    toolchain = go_toolchain()

    assert (toolchain.memory, toolchain.pids, toolchain.cache_volume) == ("768m", 256, CACHE)


def test_jdt_ls_in_a_sidecar_runs_on_the_images_jdk_whatever_this_machine_selects():
    assert sidecar_server(JDTLS, FOLDER).jdks is None


def test_jdt_ls_in_a_sidecar_runs_the_same_milestone():
    assert sidecar_server(JDTLS, FOLDER).script == JDTLS.script


def test_a_node_server_runs_on_the_node_image_whatever_the_projects():
    assert sidecar_image(TYPESCRIPT_LANGUAGE_SERVER, GRADLE_IMAGE) == NODE_IMAGE


def test_jdt_ls_runs_on_the_projects_own_image():
    """Its JDK and Gradle build the project, and `cstudy start` pulled it."""
    assert sidecar_image(JDTLS, GRADLE_IMAGE) == GRADLE_IMAGE


DATA = "/work/.cs/runs/cstudy-l-41-abc/data"
CACHE = "cstudy-i-rooms-d1g3st_cache"


def java_service() -> ServiceProject:
    service = service_of(meta_from_document(java_meta_document(), "meta.yaml"))
    assert service is not None
    return service


def jdtls_toolchain(cache: str | None = CACHE) -> SidecarToolchain:
    toolchain = sidecar_toolchain(JDTLS, java_service(), DATA, cache)
    assert toolchain is not None
    return toolchain


def test_a_node_server_needs_no_toolchain():
    assert sidecar_toolchain(BASEDPYRIGHT, java_service(), DATA, CACHE) is None


def test_gradle_keeps_its_home_in_the_data_folder_and_reads_the_install_cache_read_only():
    """Gradle neither locks nor writes a read-only cache, so the app's builds go on beside it."""
    assert jdtls_toolchain().environment == {
        "GRADLE_USER_HOME": f"{DATA}/gradle",
        "GRADLE_RO_DEP_CACHE": "/cache/gradle/caches",
    }


def test_without_an_install_cache_gradle_has_no_read_only_cache():
    assert "GRADLE_RO_DEP_CACHE" not in jdtls_toolchain(None).environment


def test_gradles_project_cache_goes_to_the_data_folder():
    """Not the project's `.gradle/`, whose locks the app's builds take."""
    assert jdtls_toolchain().files == {
        "gradle/gradle.properties": f"org.gradle.projectcachedir={DATA}/project-cache\n"
    }


def test_gradle_writes_the_project_folder_it_configures():
    assert jdtls_toolchain().writable_project


def test_jdt_ls_gets_room_for_its_heap_and_a_gradle_daemon():
    toolchain = jdtls_toolchain()

    assert (toolchain.memory, toolchain.pids, toolchain.cache_volume) == ("2g", 512, CACHE)
