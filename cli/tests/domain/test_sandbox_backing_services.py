"""A problem's backing services, merged into the stack `cstudy` generates
(docs/specs/service-projects.md#backing-services), and the services the grader may reach."""

from typing import Any

import pytest

from coding_study.domain.sandbox import (
    APP_SERVICE,
    BOOTSTRAP_SERVICE,
    FORWARD_SERVICE,
    GRADE_SETUP_SERVICE,
    MOCK_SERVICE,
    RESET_PREPARE_SERVICE,
    AppContainer,
    BackingServices,
    GradeSetup,
    MockServerInput,
    OneShot,
    SandboxPaths,
    SandboxUser,
    StackIdentity,
    StackKind,
    StackPlan,
    backing_bind_sources,
    backing_images,
    reach_listen_ports,
    stack_document,
)

RUN = "/work/.cs/runs/cstudy-t-41-abc"
IDENTITY = StackIdentity("cstudy-t-41-abc", StackKind.TEST, "d1g3st", "rooms", 41)
POSTGRES = "postgres:17.11-alpine@sha256:3540"
REDIS = "redis:7.4.12-alpine@sha256:c5d3"
DB: dict[str, Any] = {
    "image": POSTGRES,
    "user": "postgres",
    "environment": {"POSTGRES_PASSWORD": "app"},
    "volumes": ["pgdata:/var/lib/postgresql/data", "./initdb:/docker-entrypoint-initdb.d"],
    "tmpfs": ["/var/run/postgresql:mode=1777"],
    "mem_limit": "256m",
    "pids_limit": 128,
    "healthcheck": {"test": ["CMD", "pg_isready"]},
}
COMPOSE: dict[str, Any] = {
    "services": {
        "db": DB,
        "cache": {
            "image": REDIS,
            "depends_on": ["db"],
            "mem_limit": "64m",
            "pids_limit": 32,
            "healthcheck": {"test": ["CMD", "redis-cli", "ping"]},
        },
    },
    "volumes": {"pgdata": None},
}
BACKING = BackingServices(COMPOSE, "/content/problems/5903-fixture/services")


def plan(**changes: Any) -> StackPlan:
    fields: dict[str, Any] = {
        "identity": IDENTITY,
        "user": SandboxUser(501, 20),
        "paths": SandboxPaths(project="/work/projects/rooms", run=RUN),
        "app": AppContainer("node:24-slim@sha256:0123", ("node", "s.ts"), 8000, {"PORT": "8000"}),
        "backing": BACKING,
        **changes,
    }
    return StackPlan(**fields)


def document(**changes: Any) -> dict[str, Any]:
    return stack_document(plan(**changes))


def service(name: str, **changes: Any) -> dict[str, Any]:
    return document(**changes)["services"][name]


def test_each_backing_service_lands_in_the_stack_under_its_own_name():
    assert service("db")["image"] == POSTGRES


def test_a_backing_service_joins_the_sandbox_network_only():
    assert service("db")["networks"] == ["sandbox"]


def test_a_backing_service_carries_the_containers_labels():
    assert service("db")["labels"] == IDENTITY.container_labels


def test_a_backing_service_holds_no_capability_and_gains_no_privilege():
    found = service("db")

    assert found["cap_drop"] == ["ALL"]
    assert found["security_opt"] == ["no-new-privileges:true"]


def test_a_backing_service_keeps_no_more_log_than_its_limits():
    assert service("db")["logging"]["options"] == {"max-size": "10m", "max-file": "3"}


def test_a_backing_service_has_a_read_only_root_unless_the_problem_says_otherwise():
    writable = {"services": {"db": {**DB, "read_only": False}}, "volumes": {"pgdata": None}}

    assert service("db")["read_only"] is True
    assert service("db", backing=BackingServices(writable, "/f"))["read_only"] is False


def test_the_problems_own_settings_reach_the_container():
    found = service("db")

    assert (found["user"], found["mem_limit"], found["pids_limit"]) == ("postgres", "256m", 128)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("privileged", True),
        ("cap_add", ["SYS_ADMIN"]),
        ("network_mode", "host"),
        ("pid", "host"),
        ("ports", ["5432:5432"]),
        ("devices", ["/dev/sda"]),
    ],
)
def test_a_field_no_backing_service_may_set_never_reaches_the_stack(field, value):
    escaping = {"services": {"db": {**DB, field: value}}, "volumes": {"pgdata": None}}

    assert field not in service("db", backing=BackingServices(escaping, "/f"))


def test_a_bind_mount_is_a_read_only_copy_in_the_runs_folder():
    mounts = service("db")["volumes"]

    assert {
        "type": "bind",
        "source": f"{RUN}/services/initdb",
        "target": "/docker-entrypoint-initdb.d",
        "read_only": True,
    } in mounts


def test_a_long_form_bind_mount_is_a_read_only_copy_too():
    bind = {"type": "bind", "source": "./realm.json", "target": "/import/realm.json"}
    found = {"services": {"idp": {**DB, "volumes": [bind]}}}

    mounts = service("idp", backing=BackingServices(found, "/f"))["volumes"]

    assert mounts == [
        {
            "type": "bind",
            "source": f"{RUN}/services/realm.json",
            "target": "/import/realm.json",
            "read_only": True,
        }
    ]


def test_a_named_volume_mount_stays_as_the_problem_wrote_it():
    assert "pgdata:/var/lib/postgresql/data" in service("db")["volumes"]


def test_a_problem_volume_carries_the_stacks_labels():
    assert document()["volumes"]["pgdata"] == {"labels": IDENTITY.stable_labels}


def test_the_stacks_own_volume_stays_beside_the_problems():
    assert set(document()["volumes"]) == {"data", "pgdata"}


def test_the_problems_own_order_between_its_services_stays():
    assert service("cache")["depends_on"] == ["db"]


@pytest.mark.parametrize(
    "name", [APP_SERVICE, BOOTSTRAP_SERVICE, GRADE_SETUP_SERVICE, RESET_PREPARE_SERVICE]
)
def test_every_command_of_the_apps_image_waits_for_each_backing_service(name):
    setup = GradeSetup(("python", "/cstudy/problem/grading/setup.py"), "/content/grading", 2)
    commands = {
        "bootstrap": OneShot(("python", "migrate.py")),
        "grade_setup": setup,
        "reset_prepare": OneShot(("python", "reset.py")),
    }

    needs = service(name, **commands)["depends_on"]

    assert needs["db"] == needs["cache"] == {"condition": "service_healthy"}


def test_the_mock_server_does_not_wait_for_a_backing_service():
    mocks = MockServerInput(("room-vendor",), "secret", "{}")

    assert "depends_on" not in service(MOCK_SERVICE, mocks=mocks)


def test_the_mock_server_shares_sandbox_with_every_backing_service_it_may_pass_through_to():
    mocks = MockServerInput(("idp",), "secret", "{}")
    services = document(mocks=mocks)["services"]

    shared = set(services[MOCK_SERVICE]["networks"]) & set(services["db"]["networks"])

    assert shared == set(services["cache"]["networks"]) == {"sandbox"}


def test_a_stack_without_backing_services_has_only_its_own():
    found = document(backing=None)

    assert "db" not in found["services"]
    assert set(found["volumes"]) == {"data"}


def test_the_images_of_the_backing_services_are_listed_for_the_pull():
    assert backing_images(COMPOSE) == (POSTGRES, REDIS)


def test_the_bind_mount_sources_are_listed_for_the_copy():
    bind = {"type": "bind", "source": "realm.json", "target": "/import/realm.json"}
    found = {"services": {"db": DB, "idp": {**DB, "volumes": [bind]}}}

    assert backing_bind_sources(found) == ("initdb", "realm.json")


def test_a_reached_service_is_relayed_by_the_forwarder_from_a_port_of_its_own():
    reached = plan(reach=("idp:8080",))
    listen = reach_listen_ports(reached)["idp:8080"]

    command = service(FORWARD_SERVICE, reach=reached.reach)["command"]

    assert f"{listen}=idp:8080" in command


def test_a_reached_service_is_published_on_loopback_only():
    reached = plan(reach=("idp:8080",))
    listen = reach_listen_ports(reached)["idp:8080"]

    ports = service(FORWARD_SERVICE, reach=reached.reach)["ports"]

    assert f"127.0.0.1::{listen}" in ports


def test_a_reach_port_never_takes_the_apps_port():
    first = reach_listen_ports(plan(reach=("idp:8080",)))["idp:8080"]
    app = AppContainer("node:24-slim@sha256:0123", ("node", "s.ts"), first, {"PORT": str(first)})

    ports = reach_listen_ports(plan(app=app, reach=("idp:8080", "cache:6379")))

    assert first not in ports.values()
    assert len(set(ports.values())) == 2


def test_a_stack_with_no_reach_publishes_nothing_more():
    assert service(FORWARD_SERVICE)["ports"] == ["127.0.0.1::8000"]
