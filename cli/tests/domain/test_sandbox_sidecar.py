"""The language-server sidecar of a service project's code-intelligence session
(docs/specs/service-projects.md#language-servers): its compose file, its name and its sweep."""

from dataclasses import replace
from typing import Any

from coding_study.domain.sandbox import (
    JVM_SIDECAR_MEMORY,
    JVM_SIDECAR_PIDS,
    LABEL_KIND,
    LABEL_OWNER,
    LABEL_SLUG,
    NODE_IMAGE,
    SIDECAR_MEMORY,
    SIDECAR_SERVICE,
    SandboxInventory,
    SandboxUser,
    SharedFolder,
    SidecarPlan,
    SidecarToolchain,
    StackContainer,
    StackIdentity,
    StackKind,
    is_stack_name,
    leftovers_in,
    run_stack_name,
    sidecar_document,
    sidecar_files,
)

NAME = run_stack_name(StackKind.LSP, 41, "abc")
PROJECT = SharedFolder(path="/work/projects/rooms", source="/private/work/projects/rooms")
SERVERS = SharedFolder(path="/work/.cs/lsp", source="/private/work/.cs/lsp")
PLAN = SidecarPlan(
    identity=StackIdentity(NAME, StackKind.LSP, "d1g3st", "rooms", 41),
    user=SandboxUser(501, 20),
    project=PROJECT,
    servers=SERVERS,
    run="/private/work/.cs/runs/" + NAME,
)


def document() -> dict[str, Any]:
    return sidecar_document(PLAN)


def sidecar() -> dict[str, Any]:
    return document()["services"][SIDECAR_SERVICE]


def test_the_sidecar_is_a_compose_project_of_one_service():
    found = document()

    assert (found["name"], list(found["services"])) == (NAME, [SIDECAR_SERVICE])


def test_the_sidecar_declares_no_network_and_no_volume():
    assert set(document()) == {"name", "services"}


def test_the_sidecar_reaches_no_network():
    assert sidecar()["network_mode"] == "none"


def test_the_sidecar_runs_the_pinned_node_image():
    assert sidecar()["image"] == NODE_IMAGE


def test_the_node_image_is_pinned_by_digest():
    assert "@sha256:" in NODE_IMAGE


def test_the_sidecar_idles_until_a_server_runs_in_it():
    assert sidecar()["command"] == ["sleep", "infinity"]


def test_the_sidecar_is_named_after_its_stack_so_a_session_can_exec_into_it():
    assert sidecar()["container_name"] == NAME


def test_the_sidecar_is_hardened_as_the_app_is():
    found = sidecar()

    assert (found["read_only"], found["cap_drop"], found["security_opt"], found["init"]) == (
        True,
        ["ALL"],
        ["no-new-privileges:true"],
        True,
    )


def test_the_sidecar_runs_as_you():
    assert sidecar()["user"] == "501:20"


def test_the_sidecar_has_a_memory_and_a_process_limit():
    found = sidecar()

    assert (found["mem_limit"], found["pids_limit"]) == (SIDECAR_MEMORY, 128)


def test_the_sidecar_holds_a_typescript_session_within_its_memory_limit():
    """The spike measured 504 MiB at peak for TypeScript, which 512 MiB would not hold."""
    assert SIDECAR_MEMORY == "768m"


def test_the_sidecar_writes_only_its_temporary_directory():
    assert sidecar()["tmpfs"] == ["/tmp:size=64m,uid=501,gid=20,mode=1777"]


def test_the_sidecar_mounts_the_project_and_the_servers_read_only_where_the_session_names_them():
    assert sidecar()["volumes"] == [
        {
            "type": "bind",
            "source": PROJECT.source,
            "target": PROJECT.path,
            "read_only": True,
        },
        {
            "type": "bind",
            "source": SERVERS.source,
            "target": SERVERS.path,
            "read_only": True,
        },
    ]


def test_the_sidecar_works_in_the_project_folder():
    assert sidecar()["working_dir"] == PROJECT.path


def test_the_sidecar_carries_the_labels_of_its_owner():
    labels = sidecar()["labels"]

    assert (labels[LABEL_KIND], labels[LABEL_SLUG], labels[LABEL_OWNER]) == ("lsp", "rooms", "41")


def test_a_sidecar_name_is_a_stack_name():
    assert is_stack_name(NAME)


def test_a_sidecar_name_holds_its_owner():
    assert NAME == "cstudy-l-41-abc"


def sidecar_container(owner: int) -> StackContainer:
    return StackContainer(NAME, StackKind.LSP.value, "d1g3st", owner)


def test_a_sidecar_whose_cstudy_serve_is_gone_is_a_leftover():
    inventory = SandboxInventory(containers=(sidecar_container(41),))

    assert [stack.name for stack in leftovers_in(inventory, lambda _pid: False).stacks] == [NAME]


def test_a_sidecar_whose_cstudy_serve_lives_is_kept():
    inventory = SandboxInventory(containers=(sidecar_container(41),))

    assert not leftovers_in(inventory, lambda pid: pid == 41)


def test_a_sidecar_has_no_volume_to_remove():
    assert not StackKind.LSP.removes_volumes


GRADLE_IMAGE = "gradle:9.8.2-jdk25-alpine@sha256:20d4"
DATA = f"{PLAN.run}/data"
JVM_PLAN = replace(
    PLAN,
    image=GRADLE_IMAGE,
    toolchain=SidecarToolchain(
        cache_volume="cstudy-i-rooms-d1g3st_cache",
        environment={"GRADLE_USER_HOME": f"{DATA}/gradle"},
        files={"gradle/gradle.properties": "org.gradle.projectcachedir=x\n"},
        writable_project=True,
        memory=JVM_SIDECAR_MEMORY,
        pids=JVM_SIDECAR_PIDS,
    ),
    image_volumes=("/home/gradle/.gradle",),
)
"""JDT LS's sidecar: the project's own image, with its toolchain."""


def jvm_document() -> dict[str, Any]:
    return sidecar_document(JVM_PLAN)


def jvm_sidecar() -> dict[str, Any]:
    return jvm_document()["services"][SIDECAR_SERVICE]


def test_a_node_sidecar_keeps_no_data_folder():
    assert PLAN.data_directory is None


def test_a_sidecar_with_a_toolchain_runs_the_projects_own_image():
    assert jvm_sidecar()["image"] == GRADLE_IMAGE


def test_a_sidecar_with_a_toolchain_keeps_its_data_in_the_runs_folder():
    assert JVM_PLAN.data_directory == DATA


def test_a_sidecar_with_a_toolchain_mounts_what_gradle_needs():
    """The project read-write, as the app's, but its `.devcontainer`, which a host tool obeys; the
    servers read-only; the data folder read-write where it is; the install cache read-only."""
    assert jvm_sidecar()["volumes"] == [
        {"type": "bind", "source": PROJECT.source, "target": PROJECT.path},
        {
            "type": "bind",
            "source": f"{PROJECT.source}/.devcontainer",
            "target": f"{PROJECT.path}/.devcontainer",
            "read_only": True,
        },
        {"type": "bind", "source": SERVERS.source, "target": SERVERS.path, "read_only": True},
        {"type": "bind", "source": DATA, "target": DATA},
        "cache:/cache:ro",
    ]


def test_the_install_cache_is_the_install_stacks_own_volume():
    volumes = jvm_document()["volumes"]

    assert volumes == {"cache": {"external": True, "name": "cstudy-i-rooms-d1g3st_cache"}}


def test_a_sidecar_with_a_toolchain_runs_with_its_variables():
    assert jvm_sidecar()["environment"] == {
        "HOME": "/tmp/home",
        "TMPDIR": "/tmp",
        "GRADLE_USER_HOME": f"{DATA}/gradle",
    }


def test_the_images_own_volumes_are_small_temporary_folders():
    """Docker would otherwise make an anonymous volume there, which outlives the sidecar."""
    assert jvm_sidecar()["tmpfs"][1] == "/home/gradle/.gradle:size=16m,uid=501,gid=20,mode=0700"


def test_a_jvm_sidecar_has_room_for_jdt_ls_and_a_gradle_daemon():
    found = jvm_sidecar()

    assert (found["mem_limit"], found["pids_limit"]) == ("2g", 512)


def test_a_jvm_sidecar_reaches_no_network_either():
    assert jvm_sidecar()["network_mode"] == "none"


def test_the_toolchains_files_land_in_the_data_folder():
    assert sidecar_files(JVM_PLAN) == {
        f"{DATA}/gradle/gradle.properties": "org.gradle.projectcachedir=x\n"
    }


def test_a_node_sidecar_writes_no_file():
    assert sidecar_files(PLAN) == {}
