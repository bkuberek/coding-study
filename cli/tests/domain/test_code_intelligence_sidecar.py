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
    KOTLIN_LSP_LINUX,
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
    tooling_distribution,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.sandbox import GRADLE_GLIBC_IMAGE, NODE_IMAGE, SidecarToolchain
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
    "language",
    [Language.TYPESCRIPT, Language.PYTHON, Language.JAVA, Language.GO, Language.KOTLIN],
)
def test_a_service_project_with_a_sidecar_server_has_code_intelligence(language):
    assert no_code_intelligence(service_meta(language.value), language) is None


def test_a_service_project_in_another_language_has_none_yet():
    meta = service_meta("rust")

    assert no_code_intelligence(meta, Language.RUST) is NoCodeIntelligence.SERVICE_PROJECT


def test_the_service_meta_of_these_tests_is_a_service_project():
    assert service_of(service_meta("rust")) is not None


def test_a_problem_that_is_no_service_project_has_its_servers_say():
    meta = replace(service_meta("rust"), project=None)

    assert no_code_intelligence(meta, Language.RUST) is None


def test_a_server_of_no_sidecar_has_no_sidecar_variant_to_offer():
    with pytest.raises(ValueError, match="rust-analyzer runs in no sidecar"):
        sidecar_server(RUST_ANALYZER, FOLDER)


def test_the_kotlin_lsp_in_a_sidecar_is_its_linux_build():
    assert sidecar_server(KOTLIN_LSP, FOLDER) is KOTLIN_LSP_LINUX


def test_the_linux_build_runs_its_own_launcher_from_kotlin_lsp_linux():
    launch = Launch("/work/.cs/lsp", "/data", platform="linux", java_home="/opt/java/openjdk")

    assert KOTLIN_LSP_LINUX.command(launch) == (
        "/work/.cs/lsp/kotlin-lsp/linux/bin/intellij-server",
        "--stdio",
        "--system-path=/data/system",
    )


def test_the_linux_build_imports_with_the_images_jdk_and_its_gradle_home_in_the_data_folder():
    launch = Launch("/work/.cs/lsp", "/data", platform="linux", java_home="/opt/java/openjdk")
    options = KOTLIN_LSP_LINUX.environment(launch)["IJ_JAVA_OPTIONS"]

    assert (
        "-Dcom.jetbrains.ls.imports.gradle.java.home=/opt/java/openjdk" in options,
        "-Dcom.jetbrains.ls.imports.gradle.gradleUserHome=/data/gradle" in options,
        "-Dintellij.updates.enabled=false" in options,
    ) == (True, True, True)


def test_the_linux_build_keeps_its_shared_data_in_the_data_folder_not_under_the_images_home():
    """The build creates `$XDG_DATA_HOME/JetBrains` at startup; the image's `~/.local` is read-only."""
    launch = Launch("/work/.cs/lsp", "/data", platform="linux", java_home="/opt/java/openjdk")

    assert KOTLIN_LSP_LINUX.environment(launch)["XDG_DATA_HOME"] == "/data/share"


def test_the_linux_build_needs_no_jdk_of_this_machine_and_no_warm_up():
    assert (KOTLIN_LSP_LINUX.jdks, KOTLIN_LSP_LINUX.warmup) == (None, None)


def test_the_linux_build_keeps_the_license_of_this_machines():
    assert KOTLIN_LSP_LINUX.license == KOTLIN_LSP.license


def test_the_kotlin_lsp_runs_on_the_glibc_gradle_image_whatever_the_projects():
    assert sidecar_image(KOTLIN_LSP, GRADLE_IMAGE) == GRADLE_GLIBC_IMAGE


def test_the_glibc_gradle_image_is_pinned_by_digest():
    assert GRADLE_GLIBC_IMAGE.startswith("gradle:9.8.2-jdk25@sha256:")


def test_the_tooling_apis_own_distribution_is_where_gradles_wrapper_puts_it():
    """The folder's name is the base-36 MD5 of the distribution's URL, as Gradle's wrapper
    writes it: measured on the tooling API 9.7.0 that the Kotlin LSP 263.7084.0 bundles."""
    assert tooling_distribution("9.7.0") == (
        "wrapper/dists/gradle-9.7.0-bin/d4tj7w02tcgubx9zk9hbippn6/gradle-9.7.0-bin.zip.ok",
        "wrapper/dists/gradle-9.7.0-bin/d4tj7w02tcgubx9zk9hbippn6/gradle-9.7.0",
    )


def kotlin_toolchain(tooling: str | None = "9.7.0") -> SidecarToolchain:
    service = service_of(meta_from_document(java_meta_document(), "meta.yaml"))
    assert service is not None
    toolchain = sidecar_toolchain(KOTLIN_LSP_LINUX, service, DATA, CACHE, tooling)
    assert toolchain is not None
    return toolchain


def test_the_kotlin_lsps_import_finds_the_images_gradle_as_its_tooling_apis_distribution():
    marker, distribution = tooling_distribution("9.7.0")
    toolchain = kotlin_toolchain()

    assert (toolchain.links, toolchain.files[f"gradle/{marker}"]) == (
        {f"gradle/{distribution}": "/opt/gradle"},
        "",
    )


def test_without_a_known_tooling_api_nothing_is_linked():
    assert kotlin_toolchain(None).links == {}


def test_the_kotlin_lsp_gets_jdt_lss_gradle_toolchain_with_more_memory():
    toolchain = kotlin_toolchain()

    assert (
        toolchain.environment["GRADLE_RO_DEP_CACHE"],
        toolchain.writable_project,
        toolchain.memory,
    ) == ("/cache/gradle/caches", True, "3g")


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
