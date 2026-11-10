"""The generated compose file, stack names and what counts as a leftover."""

import json
from dataclasses import replace
from typing import Any

import pytest

from coding_study.domain.sandbox import (
    APP_SERVICE,
    BOOTSTRAP_SERVICE,
    CONTROL_PORT,
    DATA_OWNER_SERVICE,
    EGRESS_PROBE_SERVICE,
    FORWARD_SERVICE,
    GRADE_SETUP_SERVICE,
    INSTALL_SERVICE,
    LABEL_OWNER,
    MOCK_SERVICE,
    PYTHON_IMAGE,
    RESET_PREPARE_SERVICE,
    AppContainer,
    GradeSetup,
    InstallPlan,
    MockServerInput,
    OneShot,
    SandboxInventory,
    SandboxPaths,
    SandboxUser,
    StackContainer,
    StackIdentity,
    StackKind,
    StackPlan,
    StackResource,
    cache_volume_of,
    dev_stack_name,
    install_document,
    install_stack_name,
    is_stack_name,
    leftovers_in,
    render_compose,
    run_stack_name,
    stack_document,
    workspace_digest,
)

PROJECT = "/work/projects/rooms"
RUN = "/work/.cs/runs/cstudy-t-41-abc"
IMAGE = "node:24-slim@sha256:0123"
USER = SandboxUser(501, 20)
PATHS = SandboxPaths(project=PROJECT, run=RUN)
IDENTITY = StackIdentity("cstudy-t-41-abc", StackKind.TEST, "d1g3st", "rooms", 41)
APP = AppContainer(IMAGE, ("node", "src/server.ts"), 8000, {"PORT": "8000"})
MOCKS = MockServerInput(
    aliases=("room-vendor", "second-vendor"),
    control_token="secret",
    rendered_config="{}",
)


def plan(**changes: Any) -> StackPlan:
    return StackPlan(**{"identity": IDENTITY, "user": USER, "paths": PATHS, "app": APP, **changes})


def document_of(**changes: Any) -> dict[str, Any]:
    return stack_document(plan(**changes))


def services(**changes: Any) -> dict[str, Any]:
    return document_of(**changes)["services"]


def install_of() -> dict[str, Any]:
    return install_document(install_plan())


def install_plan() -> InstallPlan:
    return InstallPlan(
        identity=StackIdentity("cstudy-i-rooms-d1g3st", StackKind.INSTALL, "d1g3st", "rooms", 41),
        user=USER,
        paths=PATHS,
        image=IMAGE,
        command=("corepack", "pnpm", "install", "--frozen-lockfile", "--ignore-scripts"),
        environment={"COREPACK_HOME": "/cache/corepack"},
    )


def test_the_file_names_its_project_at_the_top():
    assert document_of()["name"] == "cstudy-t-41-abc"


@pytest.mark.parametrize(
    "service", [APP_SERVICE, DATA_OWNER_SERVICE, FORWARD_SERVICE, MOCK_SERVICE, BOOTSTRAP_SERVICE]
)
def test_every_generated_container_is_hardened(service):
    found = services(mocks=MOCKS, bootstrap=OneShot(("node", "migrate.ts")))[service]

    assert found["cap_drop"] == ["ALL"]
    assert found["security_opt"] == ["no-new-privileges:true"]
    assert found["read_only"] is True
    assert found["init"] is True
    assert found["stop_grace_period"] == "2s"
    assert found["mem_limit"]
    assert found["pids_limit"]


def test_only_the_volume_owner_keeps_a_capability():
    assert services()[DATA_OWNER_SERVICE]["cap_add"] == ["CHOWN"]
    assert "cap_add" not in services()[APP_SERVICE]


def test_the_app_runs_as_the_host_user_in_the_project_folder():
    app = services()[APP_SERVICE]

    assert app["user"] == "501:20"
    assert app["working_dir"] == PROJECT


def test_the_app_runs_its_command_as_the_container_command():
    assert services()[APP_SERVICE]["command"] == ["node", "src/server.ts"]


def test_the_project_folder_is_mounted_at_its_own_path():
    assert {
        "type": "bind",
        "source": PROJECT,
        "target": PROJECT,
    } in services()[APP_SERVICE]["volumes"]


def test_the_devcontainer_folder_is_a_read_only_sub_mount():
    assert {
        "type": "bind",
        "source": f"{PROJECT}/.devcontainer",
        "target": f"{PROJECT}/.devcontainer",
        "read_only": True,
    } in services()[APP_SERVICE]["volumes"]


def test_a_one_line_passwd_is_mounted_read_only_for_the_host_uid():
    assert {
        "type": "bind",
        "source": f"{RUN}/passwd",
        "target": "/etc/passwd",
        "read_only": True,
    } in services()[APP_SERVICE]["volumes"]


def test_nothing_above_the_project_folder_is_mounted():
    sources = [
        volume["source"]
        for volume in services()[APP_SERVICE]["volumes"]
        if isinstance(volume, dict)
    ]

    assert all(source.startswith((PROJECT, RUN)) for source in sources)


def test_the_docker_socket_is_never_mounted():
    text = render_compose(stack_document(plan(mocks=MOCKS)))

    assert "docker.sock" not in text


def test_home_and_temporary_files_live_on_a_tmpfs_of_the_user():
    app = services()[APP_SERVICE]

    assert app["environment"]["HOME"] == "/tmp/home"
    assert app["environment"]["TMPDIR"] == "/tmp"
    assert app["tmpfs"] == ["/tmp:size=128m,uid=501,gid=20,mode=1777"]


def test_the_app_environment_is_the_declared_one_and_the_fixed_variables():
    assert services()[APP_SERVICE]["environment"] == {
        "PORT": "8000",
        "CSTUDY_DATA_DIR": "/data",
        "HOME": "/tmp/home",
        "TMPDIR": "/tmp",
    }


def test_the_app_is_on_the_sandbox_network_only():
    assert services()[APP_SERVICE]["networks"] == ["sandbox"]


def test_the_sandbox_network_is_internal_and_the_edge_is_not():
    networks = document_of()["networks"]

    assert networks["sandbox"]["internal"] is True
    assert "internal" not in networks["edge"]


def test_the_sandbox_network_gives_this_machine_no_address_and_the_edge_keeps_its_own():
    networks = document_of()["networks"]

    assert networks["sandbox"]["driver_opts"] == {"com.docker.network.bridge.inhibit_ipv4": "true"}
    assert "driver_opts" not in networks["edge"]


def test_every_network_the_app_or_the_mock_server_joins_has_ipv6_off_explicitly():
    found = document_of(mocks=MOCKS)
    joined = {
        name
        for service in (APP_SERVICE, MOCK_SERVICE)
        for name in found["services"][service]["networks"]
    }

    assert joined == {"sandbox"}
    assert all(found["networks"][name]["enable_ipv6"] is False for name in joined)


def test_the_egress_probe_tries_the_gateways_from_its_environment():
    command = services()[EGRESS_PROBE_SERVICE]["command"]

    assert "CSTUDY_EGRESS_HOSTS" in command[-1]
    assert "errno.ECONNREFUSED" in command[-1]
    compile(command[-1], "egress-probe", "exec")


def test_the_forwarder_joins_both_networks():
    assert services()[FORWARD_SERVICE]["networks"] == ["sandbox", "edge"]


def test_the_forwarder_publishes_the_app_on_loopback_with_a_dynamic_port():
    assert services()[FORWARD_SERVICE]["ports"] == ["127.0.0.1::8000"]


def test_the_forwarder_relays_the_app_port():
    assert services()[FORWARD_SERVICE]["command"] == [
        "python",
        "-I",
        "/cstudy/forward.py",
        "8000=app:8000",
    ]


def test_the_forwarder_also_publishes_the_control_port_with_mock_servers():
    forward = services(mocks=MOCKS)[FORWARD_SERVICE]

    assert forward["ports"] == ["127.0.0.1::8000", f"127.0.0.1::{CONTROL_PORT}"]
    assert forward["command"][-1] == f"{CONTROL_PORT}=cstudy-mocks:{CONTROL_PORT}"


DEV_IDENTITY = StackIdentity("cstudy-d-rooms-d1g3st", StackKind.DEV, "d1g3st", "rooms", 41)


def test_a_dev_stack_publishes_its_debug_port_on_loopback():
    forward = services(identity=DEV_IDENTITY, debug_port=9229)[FORWARD_SERVICE]

    assert forward["ports"] == ["127.0.0.1::8000", "127.0.0.1::9229"]


def test_a_dev_stack_relays_its_debug_port_to_the_app():
    forward = services(identity=DEV_IDENTITY, debug_port=9229)[FORWARD_SERVICE]

    assert forward["command"][-1] == "9229=app:9229"


@pytest.mark.parametrize("kind", [StackKind.TEST, StackKind.GRADED])
def test_a_test_or_graded_stack_never_publishes_a_debug_port(kind):
    identity = StackIdentity("cstudy-g-41-abc", kind, "d1g3st", "rooms", 41)

    forward = services(identity=identity, debug_port=9229)[FORWARD_SERVICE]

    assert forward["ports"] == ["127.0.0.1::8000"]


def test_only_the_forwarder_publishes_anything():
    published = [
        name for name, service in services(mocks=MOCKS).items() if service.get("ports") is not None
    ]

    assert published == [FORWARD_SERVICE]


def test_the_stack_has_no_mock_container_without_mock_servers():
    assert MOCK_SERVICE not in services()


def test_each_mock_server_name_is_an_alias_of_one_container():
    mocks = services(mocks=MOCKS)[MOCK_SERVICE]

    assert mocks["networks"] == {"sandbox": {"aliases": ["room-vendor", "second-vendor"]}}


def test_the_mock_code_and_configs_are_mounted_read_only_from_the_run_folder():
    volumes = services(mocks=MOCKS)[MOCK_SERVICE]["volumes"]

    assert all(volume["read_only"] and volume["source"].startswith(RUN) for volume in volumes)


def test_the_control_token_is_in_no_compose_file_only_in_the_rendered_config():
    assert "secret" not in json.dumps(services(mocks=MOCKS))


def test_the_mock_container_runs_the_program_from_its_folder_on_its_config():
    command = services(mocks=MOCKS)[MOCK_SERVICE]["command"]

    assert command == ["python", "-I", "/cstudy/mock_server", "/cstudy/mocks.json"]


def test_nothing_of_the_mock_servers_is_mounted_in_the_app():
    app = services(mocks=MOCKS)[APP_SERVICE]

    assert "mock" not in json.dumps(app["volumes"])


def test_the_app_and_its_commands_wait_for_the_mock_servers():
    found = services(mocks=MOCKS, bootstrap=OneShot(("node", "m.ts")))

    assert found[APP_SERVICE]["depends_on"][MOCK_SERVICE] == {"condition": "service_healthy"}
    assert found[BOOTSTRAP_SERVICE]["depends_on"][MOCK_SERVICE] == {"condition": "service_healthy"}


def test_reset_prepare_runs_after_bootstrap_and_before_the_app():
    found = services(
        bootstrap=OneShot(("node", "m.ts")), reset_prepare=OneShot(("node", "reset.ts"))
    )

    assert found[RESET_PREPARE_SERVICE]["environment"]["CSTUDY_RESET_PHASE"] == "prepare"
    assert BOOTSTRAP_SERVICE in found[RESET_PREPARE_SERVICE]["depends_on"]
    assert RESET_PREPARE_SERVICE in found[APP_SERVICE]["depends_on"]
    assert BOOTSTRAP_SERVICE not in found[APP_SERVICE]["depends_on"]


def test_the_egress_probe_is_on_the_internal_network_only_and_stays_out_of_up():
    probe = services()[EGRESS_PROBE_SERVICE]

    assert probe["networks"] == ["sandbox"]
    assert probe["profiles"] == [EGRESS_PROBE_SERVICE]


def test_the_egress_probe_is_hardened_like_a_helper():
    probe = services()[EGRESS_PROBE_SERVICE]

    assert probe["read_only"] is True
    assert probe["cap_drop"] == ["ALL"]
    assert probe["user"] == "65534:65534"


def test_the_app_waits_for_the_volume_owner():
    assert services()[APP_SERVICE]["depends_on"] == {
        DATA_OWNER_SERVICE: {"condition": "service_completed_successfully"}
    }


def test_bootstrap_is_a_one_shot_the_app_depends_on():
    found = services(bootstrap=OneShot(("node", "migrate.ts")))

    assert found[BOOTSTRAP_SERVICE]["command"] == ["node", "migrate.ts"]
    assert found[APP_SERVICE]["depends_on"][BOOTSTRAP_SERVICE] == {
        "condition": "service_completed_successfully"
    }


def test_grade_setup_runs_before_bootstrap_with_the_project_read_only():
    found = services(
        bootstrap=OneShot(("node", "migrate.ts")),
        grade_setup=GradeSetup(("node", "/cstudy/problem/grading/s.ts"), "/content/p/grading", 2),
    )
    setup = found[GRADE_SETUP_SERVICE]

    assert found[BOOTSTRAP_SERVICE]["depends_on"][GRADE_SETUP_SERVICE] == {
        "condition": "service_completed_successfully"
    }
    assert {
        "type": "bind",
        "source": PROJECT,
        "target": PROJECT,
        "read_only": True,
    } in setup["volumes"]
    assert setup["environment"]["CSTUDY_PROBLEM_DIR"] == "/cstudy/problem"
    assert setup["environment"]["CSTUDY_GRADED_LEVEL"] == "2"


def test_the_grading_folder_never_reaches_the_app():
    found = services(grade_setup=GradeSetup(("node", "s.ts"), "/content/p/grading", 1))

    assert "/content/p/grading" not in json.dumps(found[APP_SERVICE])
    assert "/content/p/grading" in json.dumps(found[GRADE_SETUP_SERVICE])


def test_an_idle_app_has_no_command_of_its_own():
    app = AppContainer(IMAGE, None, 8000, {})

    assert services(app=app)[APP_SERVICE]["command"] == ["sleep", "infinity"]


def test_every_container_caps_its_log_on_your_disk():
    """Per container: the engine's own settings are yours."""
    every = {**services(mocks=MOCKS), **install_of()["services"]}

    assert {name: service["logging"] for name, service in every.items()} == {
        name: {"driver": "json-file", "options": {"max-size": "10m", "max-file": "3"}}
        for name in every
    }


def test_the_owner_pid_is_on_every_container():
    found = services(mocks=MOCKS, bootstrap=OneShot(("x",)))

    assert all(service["labels"][LABEL_OWNER] == "41" for service in found.values())


def test_networks_carry_stable_labels_without_the_owner():
    networks = document_of()["networks"]

    assert all(
        network["labels"]
        == {"cstudy.kind": "test", "cstudy.workspace": "d1g3st", "cstudy.slug": "rooms"}
        for network in networks.values()
    )


def test_volumes_carry_stable_labels_without_the_owner():
    assert document_of()["volumes"]["data"]["labels"] == {
        "cstudy.kind": "test",
        "cstudy.workspace": "d1g3st",
        "cstudy.slug": "rooms",
    }


def test_the_rendered_file_has_no_interpolation():
    app = AppContainer(IMAGE, ("sh", "-c", "echo ${HOME} $1"), 8000, {"PATTERN": "$PATH"})

    text = render_compose(stack_document(plan(app=app)))

    assert "${HOME}" not in text.replace("$${HOME}", "")
    assert '"echo $${HOME} $$1"' in text
    assert '"$$PATH"' in text


def test_the_rendered_file_is_json_which_compose_reads_as_yaml():
    assert json.loads(render_compose(document_of()))["name"] == "cstudy-t-41-abc"


def test_the_helpers_use_the_pinned_python_image():
    found = services(mocks=MOCKS)

    assert found[FORWARD_SERVICE]["image"] == PYTHON_IMAGE
    assert found[MOCK_SERVICE]["image"] == PYTHON_IMAGE
    assert found[DATA_OWNER_SERVICE]["image"] == PYTHON_IMAGE
    assert "@sha256:" in PYTHON_IMAGE


def test_install_runs_on_its_own_ordinary_network():
    document = install_of()

    assert document["services"][INSTALL_SERVICE]["networks"] == ["egress"]
    assert "internal" not in document["networks"]["egress"]


def test_install_holds_no_mock_server_app_or_service():
    assert set(install_of()["services"]) == {
        "cache-owner",
        INSTALL_SERVICE,
    }


def test_install_runs_hardened_as_the_host_user():
    install = install_of()["services"][INSTALL_SERVICE]

    assert install["user"] == "501:20"
    assert install["cap_drop"] == ["ALL"]
    assert install["read_only"] is True


def test_install_mounts_the_project_and_its_cache_and_nothing_else():
    install = install_of()["services"][INSTALL_SERVICE]

    assert {"type": "bind", "source": PROJECT, "target": PROJECT} in install["volumes"]
    assert "cache:/cache" in install["volumes"]
    assert f"{RUN}/passwd" in json.dumps(install["volumes"])
    assert len(install["volumes"]) == 4


def test_install_cannot_rewrite_the_devcontainer_folder():
    install = install_of()["services"][INSTALL_SERVICE]

    assert {
        "type": "bind",
        "source": f"{PROJECT}/.devcontainer",
        "target": f"{PROJECT}/.devcontainer",
        "read_only": True,
    } in install["volumes"]


def test_install_waits_for_its_cache_to_be_owned():
    install = install_of()["services"][INSTALL_SERVICE]

    assert install["depends_on"] == {"cache-owner": {"condition": "service_completed_successfully"}}


def test_the_install_cache_carries_stable_labels():
    assert install_of()["volumes"]["cache"]["labels"]["cstudy.kind"] == ("install")


def test_the_install_cache_is_named_after_its_install_stack():
    assert cache_volume_of("cstudy-i-rooms-d1g3st") == "cstudy-i-rooms-d1g3st_cache"


def test_an_install_plan_names_its_cache_volume():
    assert install_plan().cache_volume == "cstudy-i-rooms-d1g3st_cache"


CACHED_APP = replace(APP, install_cache="cstudy-i-rooms-d1g3st_cache")
"""An app whose dependencies live in the install cache, as Gradle's do."""


def test_an_app_keeps_out_of_the_install_cache_by_default():
    assert "cache:/cache" not in services()[APP_SERVICE]["volumes"]


@pytest.mark.parametrize("service", [APP_SERVICE, BOOTSTRAP_SERVICE, RESET_PREPARE_SERVICE])
def test_an_app_that_keeps_its_dependencies_in_the_cache_mounts_it(service):
    found = services(
        app=CACHED_APP,
        bootstrap=OneShot(("java", "Seed.java")),
        reset_prepare=OneShot(("java", "Reset.java")),
    )

    assert "cache:/cache" in found[service]["volumes"]


def test_grade_setup_mounts_the_cache_of_an_app_that_keeps_its_dependencies_there():
    setup = GradeSetup(("java", "{problem}/grading/Load.java"), "/problems/rooms/grading", 1)

    found = services(app=CACHED_APP, grade_setup=setup)[GRADE_SETUP_SERVICE]

    assert "cache:/cache" in found["volumes"]


def test_a_stack_refers_to_the_install_cache_and_never_owns_it():
    volume = document_of(app=CACHED_APP)["volumes"]["cache"]

    assert volume == {"external": True, "name": "cstudy-i-rooms-d1g3st_cache"}


def test_a_stack_declares_no_cache_for_an_app_that_keeps_out_of_it():
    assert "cache" not in document_of()["volumes"]


def test_a_volume_the_image_declares_gets_a_small_tmpfs_of_the_user():
    app = services(app=replace(APP, image_volumes=("/home/gradle/.gradle",)))[APP_SERVICE]

    assert "/home/gradle/.gradle:size=16m,uid=501,gid=20,mode=0700" in app["tmpfs"]


@pytest.mark.parametrize("path", ["/tmp", "/data", "/cache"])
def test_a_declared_volume_that_cstudy_mounts_itself_gets_no_second_mount(path):
    app = services(app=replace(APP, image_volumes=(path,)))[APP_SERVICE]

    assert app["tmpfs"] == ["/tmp:size=128m,uid=501,gid=20,mode=1777"]


def test_install_covers_a_volume_the_image_declares_with_a_tmpfs():
    covered = replace(install_plan(), image_volumes=("/home/gradle/.gradle",))
    document: dict[str, Any] = install_document(covered)

    install = document["services"][INSTALL_SERVICE]

    assert "/home/gradle/.gradle:size=16m,uid=501,gid=20,mode=0700" in install["tmpfs"]


def test_a_run_name_holds_its_kind_and_its_owner():
    assert run_stack_name(StackKind.TEST, 41, "abc") == "cstudy-t-41-abc"
    assert run_stack_name(StackKind.GRADED, 41, "abc") == "cstudy-g-41-abc"


def test_a_dev_name_is_stable_per_project_and_workspace():
    assert dev_stack_name("rooms", "d1g3st") == "cstudy-d-rooms-d1g3st"


def test_an_install_name_is_stable_per_project_and_workspace():
    assert install_stack_name("rooms", "d1g3st") == "cstudy-i-rooms-d1g3st"


def test_a_workspace_digest_is_short_and_depends_on_the_path():
    assert len(workspace_digest("/a")) == 8
    assert workspace_digest("/a") != workspace_digest("/b")


def test_only_test_and_graded_stacks_remove_their_volumes():
    assert StackKind.TEST.removes_volumes
    assert StackKind.GRADED.removes_volumes
    assert not StackKind.DEV.removes_volumes
    assert not StackKind.INSTALL.removes_volumes


def container(stack: str, kind: str = "test", owner: int | None = 41) -> StackContainer:
    return StackContainer(stack, kind, "d1g3st", owner)


def alive(*pids: int):
    return lambda pid: pid in pids


def test_a_stack_whose_owner_is_gone_is_a_leftover():
    inventory = SandboxInventory(containers=(container("cstudy-t-41-abc"),))

    found = leftovers_in(inventory, alive())

    assert [stack.name for stack in found.stacks] == ["cstudy-t-41-abc"]


def test_a_stack_whose_owner_lives_is_kept():
    inventory = SandboxInventory(containers=(container("cstudy-t-41-abc"),))

    assert not leftovers_in(inventory, alive(41))


def test_a_stack_with_one_container_of_a_live_owner_is_kept():
    inventory = SandboxInventory(
        containers=(container("cstudy-t-41-abc", owner=7), container("cstudy-t-41-abc", owner=41))
    )

    assert not leftovers_in(inventory, alive(41))


def test_a_container_with_an_unreadable_owner_counts_as_gone():
    inventory = SandboxInventory(containers=(container("cstudy-t-41-abc", owner=None),))

    assert leftovers_in(inventory, alive(41)).stacks


def test_a_test_leftover_loses_its_volumes():
    inventory = SandboxInventory(containers=(container("cstudy-t-41-abc"),))

    assert leftovers_in(inventory, alive()).stacks[0].removes_volumes


def test_a_dev_leftover_keeps_its_volumes():
    inventory = SandboxInventory(containers=(container("cstudy-d-rooms-x", kind="dev"),))

    assert not leftovers_in(inventory, alive()).stacks[0].removes_volumes


def test_an_unknown_kind_keeps_its_volumes():
    inventory = SandboxInventory(containers=(container("cstudy-t-41-abc", kind="later"),))

    assert not leftovers_in(inventory, alive()).stacks[0].removes_volumes


def resource(name: str, stack: str, kind: str = "test") -> StackResource:
    return StackResource(name, stack, kind, "d1g3st")


NETWORK = "cstudy-t-41-abc_sandbox"
VOLUME = "cstudy-g-41-abc_data"


def test_a_network_of_a_dead_run_with_no_container_is_a_stray():
    inventory = SandboxInventory(networks=(resource(NETWORK, "cstudy-t-41-abc"),))

    assert leftovers_in(inventory, alive()).networks == (NETWORK,)


def test_a_volume_of_a_dead_run_with_no_container_is_a_stray():
    inventory = SandboxInventory(volumes=(resource(VOLUME, "cstudy-g-41-abc", "graded"),))

    assert leftovers_in(inventory, alive()).volumes == (VOLUME,)


def test_a_network_of_a_live_run_is_kept_while_its_containers_are_being_made():
    inventory = SandboxInventory(networks=(resource("n", "cstudy-t-41-abc"),))

    assert not leftovers_in(inventory, alive(41))


def test_a_network_of_a_stack_with_containers_goes_with_the_stack():
    inventory = SandboxInventory(
        containers=(container("cstudy-t-41-abc"),),
        networks=(resource(NETWORK, "cstudy-t-41-abc"),),
    )

    assert leftovers_in(inventory, alive()).networks == ()


def test_a_dev_volume_is_never_a_stray():
    inventory = SandboxInventory(volumes=(resource("v", "cstudy-d-rooms-x", "dev"),))

    assert not leftovers_in(inventory, alive())


def test_an_install_cache_is_never_a_stray():
    inventory = SandboxInventory(volumes=(resource("v", "cstudy-i-rooms-x", "install"),))

    assert not leftovers_in(inventory, alive())


def test_the_sweep_of_a_workspace_leaves_other_workspaces_alone():
    inventory = SandboxInventory(
        containers=(StackContainer("cstudy-t-41-abc", "test", "other", 41),),
        networks=(StackResource("n", "cstudy-t-9-abc", "test", "other"),),
    )

    assert not leftovers_in(inventory, alive(), "d1g3st")


def test_without_a_workspace_every_workspace_counts():
    inventory = SandboxInventory(containers=(StackContainer("cstudy-t-41-abc", "test", "o", 41),))

    assert leftovers_in(inventory, alive()).stacks


def test_leftovers_are_counted_for_the_doctor_row():
    inventory = SandboxInventory(
        containers=(container("cstudy-t-41-abc"),),
        networks=(resource("cstudy-t-9-abc_sandbox", "cstudy-t-9-abc"),),
        volumes=(resource("cstudy-t-9-abc_data", "cstudy-t-9-abc"),),
    )

    assert leftovers_in(inventory, alive()).count == 3


NOT_OUR_NAMES = (
    "../../../victim",
    "/tmp/victim",
    "",
    "cstudy-t-1-a/../../victim",
    "cstudy-t-1-a/b",
    "cstudy-t-",
    "cstudy-x-1-a",
    "cstudy",
    "other-project",
    "cstudy-t-1-A",
    "cstudy-t-1-a\n",
)


@pytest.mark.parametrize("name", NOT_OUR_NAMES)
def test_only_a_generated_name_is_a_stack_name(name):
    assert not is_stack_name(name)


@pytest.mark.parametrize(
    "name",
    [
        run_stack_name(StackKind.TEST, 41, "abc"),
        run_stack_name(StackKind.GRADED, 41, "abc"),
        dev_stack_name("5901-fixture-rooms", "d1g3st"),
        install_stack_name("5901-fixture-rooms", "d1g3st"),
        "cstudy-t-41-abc_sandbox",
    ],
)
def test_every_generated_name_is_a_stack_name(name):
    assert is_stack_name(name)


@pytest.mark.parametrize("name", NOT_OUR_NAMES)
def test_a_container_labelled_with_another_name_is_no_stack(name):
    inventory = SandboxInventory(containers=(container(name, owner=None),))

    assert not leftovers_in(inventory, alive()).stacks


@pytest.mark.parametrize("name", NOT_OUR_NAMES)
def test_a_network_labelled_with_another_stack_is_no_stray(name):
    inventory = SandboxInventory(networks=(resource("cstudy-t-1-a_sandbox", name),))

    assert not leftovers_in(inventory, alive()).networks


@pytest.mark.parametrize("name", NOT_OUR_NAMES)
def test_a_volume_labelled_with_another_stack_is_no_stray(name):
    inventory = SandboxInventory(volumes=(resource("cstudy-t-1-a_data", name),))

    assert not leftovers_in(inventory, alive()).volumes


@pytest.mark.parametrize("name", NOT_OUR_NAMES)
def test_a_network_of_another_name_is_no_stray(name):
    inventory = SandboxInventory(networks=(resource(name, "cstudy-t-1-a"),))

    assert not leftovers_in(inventory, alive()).networks


@pytest.mark.parametrize("name", NOT_OUR_NAMES)
def test_a_volume_of_another_name_is_no_stray(name):
    inventory = SandboxInventory(volumes=(resource(name, "cstudy-t-1-a"),))

    assert not leftovers_in(inventory, alive()).volumes
