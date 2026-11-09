"""S20, S21, S22 and S23: a service project's mock configs, compose file and HTTP cases."""

from dataclasses import replace

import pytest

from coding_study.domain.cases import Case, Expected, OperationSequence
from coding_study.domain.http_case import (
    HttpCaseInput,
    HttpExpected,
    HttpRequest,
    HttpStep,
    LogAssertion,
    RequestTemplate,
)
from coding_study.domain.mock_configs import MockFiles
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Level
from coding_study.domain.project import ProjectFile, ProjectFiles, ProjectTree
from coding_study.domain.service_content_checks import (
    compose_issues,
    compose_requires_issues,
    http_case_issues,
    manifest_name_issues,
    mock_config_issues,
)
from coding_study.domain.service_project import (
    ServiceApp,
    ServiceCommands,
    ServiceMock,
    ServiceProject,
    ServiceRequires,
)

CONFIG = "mocks/room-vendor.yaml"
DIGEST = "@sha256:01d566e8d94d8c619591d78652babfccd3c6992a3dffa9ed5ab39e11cf6c70e9"
API = "The scenarios: `outage`.\n"
LEVELS = (Level(1, "One"), Level(2, "Two"))


def service(**changes: object) -> ServiceProject:
    fields: dict[str, object] = {
        "image": f"node:24-slim{DIGEST}",
        "commands": ServiceCommands(run=("node", "s.ts"), test=("node", "--test")),
        "app": ServiceApp("PORT", 8000, "/health"),
        "env": {"PORT": "8000"},
        "requires": ServiceRequires(),
        "mocks": (ServiceMock("room-vendor", CONFIG),),
        **changes,
    }
    return ServiceProject(**fields)  # type: ignore[arg-type]


def config(**scenarios: object) -> dict[str, object]:
    return {
        "routes": [{"id": "rooms", "method": "GET", "path": "/r", "response": {"status": 200}}],
        "scenarios": scenarios or {"outage": {"visible": True, "status": 503}},
    }


def files_of(
    document: dict[str, object] | None = None,
    *,
    bodies: dict[str, str | None] | None = None,
    api: str | None = API,
    starter_api: str | None = API,
) -> ProjectFiles:
    tree = () if starter_api is None else (_file("vendors/room-vendor/API.md", starter_api),)
    mock = MockFiles(document or config(), bodies or {}, api)
    return ProjectFiles(ProjectTree(tree), mocks={"room-vendor": mock})


def _file(path: str, text: str) -> ProjectFile:
    return ProjectFile(path, len(text), text)


def messages(found) -> list[str]:
    return [message for _where, message in found]


def s20(files: ProjectFiles, project: ServiceProject | None = None) -> list[str]:
    return messages(mock_config_issues(project or service(), files))


def test_a_good_mock_config_has_no_issue():
    assert s20(files_of()) == []


def test_a_config_outside_mocks_is_refused():
    project = service(mocks=(ServiceMock("room-vendor", "elsewhere/v.yaml"),))

    assert any("lies in mocks/" in message for message in s20(files_of(), project))


def test_a_body_file_that_leaves_mocks_is_refused():
    document = config(leak={"body_file": "../grading/secret.json"})

    assert any("leaves its folder" in message for message in s20(files_of(document)))


def test_a_body_file_that_is_not_there_is_refused():
    document = config(gone={"body_file": "bodies/gone.json"})

    assert any("is not there" in message for message in s20(files_of(document)))


def test_a_body_file_that_is_not_text_is_refused():
    document = config(binary={"body_file": "bodies/b.bin"})

    found = s20(files_of(document, bodies={"bodies/b.bin": None}))

    assert any("not UTF-8" in message for message in found)


def test_a_delay_over_the_bound_is_refused():
    document = config(slow={"delay_ms": 3001})

    assert any("at most 3 s" in message for message in s20(files_of(document)))


def test_a_delay_at_the_bound_is_allowed():
    assert s20(files_of(config(slow={"delay_ms": 3000}))) == []


def test_a_route_delay_over_the_bound_is_refused():
    document: dict[str, object] = {
        "routes": [
            {
                "id": "rooms",
                "method": "GET",
                "path": "/r",
                "response": {"status": 200, "delay_ms": 3500},
            }
        ]
    }

    assert any("at most 3 s" in message for message in s20(files_of(document, api="")))


def test_a_retry_after_over_the_bound_is_refused_in_a_sequence_too():
    document = config(limited={"sequence": [{"status": 429, "headers": {"Retry-After": "4"}}]})

    assert any("at most 3 s" in message for message in s20(files_of(document)))


def test_a_retry_after_that_is_not_whole_seconds_is_refused():
    document = config(limited={"status": 429, "headers": {"retry-after": "soon"}})

    assert any("whole seconds" in message for message in s20(files_of(document)))


def test_the_vendor_documentation_is_required():
    assert any("API.md" in message for message in s20(files_of(api=None)))


def test_the_starters_copy_is_required():
    assert any("copy" in message for message in s20(files_of(starter_api=None)))


def test_the_starters_copy_must_be_byte_identical():
    assert any("byte" in message for message in s20(files_of(starter_api=API + " ")))


def test_the_documentation_must_list_a_visible_scenario():
    document = config(
        outage={"visible": True, "status": 503}, slow={"visible": True, "delay_ms": 100}
    )

    assert any("slow" in message for message in s20(files_of(document)))


def test_the_documentation_must_not_name_a_hidden_scenario():
    text = "`outage` and `secret_one`\n"
    document = config(outage={"visible": True, "status": 503}, secret_one={"status": 429})

    found = s20(files_of(document, api=text, starter_api=text))

    assert any("hidden" in message and "secret_one" in message for message in found)


def passing_through(upstream: str, compose_file: object = None) -> ProjectFiles:
    files = files_of({**config(), "upstream": upstream})
    return replace(files, backing_services=compose_file)


def test_a_pass_through_may_reach_a_service_of_the_compose_file():
    assert s20(passing_through("http://db:5432", compose())) == []


def test_a_pass_through_to_what_is_no_service_of_the_compose_file_is_refused():
    found = s20(passing_through("http://keycloak:8080", compose()))

    assert any("keycloak is no service of the compose file" in message for message in found)


def test_a_pass_through_without_a_compose_file_is_refused():
    found = s20(passing_through("http://keycloak:8080"))

    assert any("keycloak is no service of the compose file" in message for message in found)


def s21(document: object, project: ServiceProject | None = None) -> list[str]:
    return messages(compose_issues(project or service(services="c.yaml"), document))


def compose_service(**changes: object) -> dict[str, object]:
    return {
        "image": f"postgres:17{DIGEST}",
        "mem_limit": "512m",
        "pids_limit": 256,
        "healthcheck": {"test": ["CMD", "true"]},
        **changes,
    }


def compose(**changes: object) -> dict[str, object]:
    return {"services": {"db": compose_service(**changes)}}


PROJECT_WITH_POSTGRES = service(services="c.yaml", requires=ServiceRequires(services=("postgres",)))


def test_a_good_compose_file_has_no_issue():
    assert s21(compose(), PROJECT_WITH_POSTGRES) == []


@pytest.mark.parametrize(
    "field",
    ["ports", "networks", "network_mode", "restart", "container_name", "privileged", "cap_add"],
)
def test_a_field_cstudy_owns_is_refused(field):
    assert any(field in message for message in s21(compose(**{field: "x"})))


def test_a_top_level_name_is_refused():
    document = {**compose(), "name": "mine"}

    assert any("name" in message for message in s21(document))


def test_an_unpinned_image_is_refused():
    assert any("digest" in message for message in s21(compose(image="postgres:17")))


def test_a_build_is_refused():
    found = s21({"services": {"db": {**compose_service(), "build": "."}}})

    assert any("build" in message for message in found)


@pytest.mark.parametrize("field", ["mem_limit", "pids_limit", "healthcheck"])
def test_a_limit_and_a_healthcheck_are_required(field):
    service_document = compose_service()
    del service_document[field]

    assert any(field in message for message in s21({"services": {"db": service_document}}))


def test_an_external_volume_is_refused():
    document = {**compose(), "volumes": {"data": {"external": True}}}

    assert any("external" in message for message in s21(document))


def test_the_docker_socket_is_refused():
    found = s21(compose(volumes=["/var/run/docker.sock:/var/run/docker.sock"]))

    assert any("socket" in message for message in found)


def test_a_bind_mount_outside_the_problem_is_refused():
    assert any("outside" in message for message in s21(compose(volumes=["/etc:/data"])))
    assert any("outside" in message for message in s21(compose(volumes=["../x:/data"])))


def test_a_long_form_bind_mount_outside_the_problem_is_refused():
    volume = {"type": "bind", "source": "/etc", "target": "/data"}

    assert any("outside" in message for message in s21(compose(volumes=[volume])))


def test_a_named_volume_and_a_bind_inside_the_problem_are_allowed():
    document = compose(volumes=["pgdata:/var/lib/data", "./seed:/seed:ro"])

    assert s21({**document, "volumes": {"pgdata": None}}, PROJECT_WITH_POSTGRES) == []


def test_an_anonymous_volume_is_refused():
    assert any("named" in message for message in s21(compose(volumes=["/var/lib/data"])))


def test_a_reserved_service_name_is_refused():
    assert any("reserved" in message for message in s21({"services": {"app": compose_service()}}))


def test_a_service_named_after_a_mock_server_is_refused():
    found = s21({"services": {"room-vendor": compose_service()}})

    assert any("mock server" in message for message in found)


def s22(document: object, project: ServiceProject) -> list[str]:
    return messages(compose_requires_issues(project, document))


def test_requires_services_must_name_the_images_repositories():
    project = service(services="c.yaml", requires=ServiceRequires(services=("redis",)))

    assert any("postgres" in message for message in s22(compose(), project))


def test_a_repository_is_its_last_path_segment():
    project = service(services="c.yaml", requires=ServiceRequires(services=("localstack",)))
    document = compose(image=f"localstack/localstack:4.14.0{DIGEST}")

    assert s22(document, project) == []


def test_s21_alone_does_not_hold_the_requires_block_to_the_file():
    project = service(services="c.yaml", requires=ServiceRequires(services=("redis",)))

    assert s21(compose(), project) == []


def test_a_compose_file_that_is_no_mapping_is_refused():
    assert any("mapping" in message for message in s21(["services"]))


def test_a_compose_file_with_no_service_is_refused():
    assert any("at least one service" in message for message in s21({"services": {}}))


@pytest.mark.parametrize(
    "field",
    [
        "pid",
        "ipc",
        "devices",
        "volumes_from",
        "userns_mode",
        "env_file",
        "extends",
        "post_start",
        "deploy",
        "security_opt",
        "labels",
        "logging",
        "cap_drop",
        "profiles",
        "extra_hosts",
        "sysctls",
    ],
)
def test_a_field_outside_what_a_backing_service_may_set_is_refused(field):
    assert any(field in message for message in s21(compose(**{field: "x"})))


@pytest.mark.parametrize("limit", [-1, 0, "many"])
def test_a_pids_limit_that_is_no_limit_is_refused(limit):
    assert any("pids_limit" in message for message in s21(compose(pids_limit=limit)))


@pytest.mark.parametrize("limit", ["0", "lots", 0, "-1m"])
def test_a_mem_limit_that_is_no_limit_is_refused(limit):
    assert any("mem_limit" in message for message in s21(compose(mem_limit=limit)))


@pytest.mark.parametrize("check", [{"disable": True}, {"test": ["NONE"]}, {"interval": "1s"}])
def test_a_healthcheck_that_checks_nothing_is_refused(check):
    assert any("healthcheck" in message for message in s21(compose(healthcheck=check)))


@pytest.mark.parametrize("name", ["data", "cache"])
def test_a_volume_named_after_the_stacks_own_is_refused(name):
    document = {**compose(volumes=[f"{name}:/var/lib/data"]), "volumes": {name: None}}

    assert any("reserved" in message for message in s21(document))


@pytest.mark.parametrize(
    "settings",
    [
        {"driver": "local"},
        {"driver_opts": {"type": "none", "o": "bind", "device": "/"}},
        {"name": "someone-elses"},
        {"labels": {"cstudy.kind": "dev"}},
    ],
)
def test_a_volume_with_settings_of_its_own_is_refused(settings):
    document = {**compose(volumes=["pgdata:/var/lib/data"]), "volumes": {"pgdata": settings}}

    assert any("pgdata" in where for where, _message in compose_issues(service(), document))


def test_a_named_volume_the_file_does_not_declare_is_refused():
    found = s21(compose(volumes=["elsewhere:/var/lib/data"]))

    assert any("elsewhere" in message and "declare" in message for message in found)


def test_a_long_form_named_volume_the_file_does_not_declare_is_refused():
    volume = {"type": "volume", "source": "data", "target": "/var/lib/data"}

    assert any("declare" in message for message in s21(compose(volumes=[volume])))


@pytest.mark.parametrize("kind", ["npipe", "image", "cluster"])
def test_a_mount_of_another_type_is_refused(kind):
    volume = {"type": kind, "source": "x", "target": "/x"}

    assert any(kind in message for message in s21(compose(volumes=[volume])))


def test_a_tmpfs_mount_is_allowed():
    volume = {"type": "tmpfs", "target": "/run/postgresql"}

    assert s21(compose(volumes=[volume]), PROJECT_WITH_POSTGRES) == []


def test_waiting_for_a_service_of_the_stacks_own_is_refused():
    assert any("app" in message for message in s21(compose(depends_on=["app"])))


def test_waiting_for_another_backing_service_is_allowed():
    document = {"services": {"db": compose_service(), "cache": compose_service(depends_on=["db"])}}

    assert s21(document) == []


@pytest.mark.parametrize("name", ["Db", "my_db", "db.1", "-db"])
def test_a_service_name_the_app_cannot_reach_by_is_refused(name):
    assert any("name" in message for message in s21({"services": {name: compose_service()}}))


def names_in(project: ServiceProject, document: object = None) -> list[str]:
    return messages(manifest_name_issues(project, document))


def test_a_url_in_env_must_name_a_service_of_the_file():
    project = service(services="c.yaml", env={"PORT": "8000", "DATABASE_URL": "postgres://x@db2/a"})

    assert any("db2" in message for message in names_in(project, compose()))


def test_a_url_in_env_that_names_a_service_of_the_file_is_fine():
    project = service(services="c.yaml", env={"PORT": "8000", "DATABASE_URL": "postgres://db/a"})

    assert names_in(project, compose()) == []


def reach(*origins: str, document: object = None) -> list[str]:
    project = service(services="c.yaml" if document else None, grader_reach=origins)
    return names_in(project, document)


def test_the_grader_may_reach_a_service_of_the_file():
    assert reach("db:5432", document=compose()) == []


def test_the_grader_may_reach_a_mock_server_on_its_port():
    assert reach("room-vendor:8080") == []


def test_the_grader_reaches_a_mock_server_on_its_port_only():
    assert any("8080" in message for message in reach("room-vendor:9000"))


def test_the_grader_may_not_reach_what_is_neither_a_service_nor_a_mock_server():
    assert any("idp" in message for message in reach("idp:8080", document=compose()))


@pytest.mark.parametrize("origin", ["app:8000", "cstudy-mocks:9000", "cstudy-forward:8000"])
def test_the_grader_reaches_none_of_the_stacks_own_containers_this_way(origin):
    assert any("reserved" in message for message in reach(origin, document=compose()))


def http_case(
    case_id: str = "h1",
    level: int | None = 1,
    *,
    visible: bool = False,
    hang_guard_ms: int | None = None,
    **fields: object,
) -> Case:
    http = HttpCaseInput(
        {"method": "GET", "path": "/a"},
        request=HttpRequest("GET", "/a"),
        expected=HttpExpected(200),
        **fields,  # type: ignore[arg-type]
    )
    return Case(
        case_id,
        http,
        Expected({"status": 200}),
        visible=visible,
        level=level,
        hang_guard_ms=hang_guard_ms,
    )


def s23(*cases: Case, **changes: object) -> list[str]:
    files = files_of(
        config(
            outage={"visible": True, "status": 503},
            limited={"status": 429, "headers": {"Retry-After": "2"}},
            sequenced={"sequence": [{"delay_ms": 3000}, {"delay_ms": 3000}, {"delay_ms": 3000}]},
        )
    )
    defaults: dict[str, object] = {
        "project": service(),
        "levels": LEVELS,
        "comparator": ComparatorSpec(ComparatorType.EXACT),
        "hang_guard_ms": None,
    }
    arguments = {**defaults, **changes}
    return messages(
        http_case_issues(
            cases,
            files,
            arguments["project"],  # type: ignore[arg-type]
            levels=arguments["levels"],  # type: ignore[arg-type]
            comparator=arguments["comparator"],  # type: ignore[arg-type]
            hang_guard_ms=arguments["hang_guard_ms"],  # type: ignore[arg-type]
        )
    )


EVERY_LEVEL = (http_case("h1", 1), http_case("h2", 2))


def test_good_cases_have_no_issue():
    assert s23(*EVERY_LEVEL) == []


def test_a_case_with_no_request_is_refused():
    other = Case("o", OperationSequence(("a",), (())), Expected(1), level=1)

    assert any("request" in message for message in s23(other, *EVERY_LEVEL))


def test_a_case_needs_a_level_it_can_reach():
    assert any("level" in message for message in s23(http_case("x", None), *EVERY_LEVEL))
    assert any("level" in message for message in s23(http_case("x", 3), *EVERY_LEVEL))


def test_every_level_has_a_case():
    assert any("level 2 has no cases" in message for message in s23(http_case("h1", 1)))


def test_levels_are_numbered_without_gaps():
    found = s23(http_case("h1", 1), levels=(Level(1, "One"), Level(3, "Three")))

    assert any("without gaps" in message for message in found)


def test_a_case_names_a_known_mock_server():
    found = s23(http_case(mocks={"nobody": "outage"}), http_case("h2", 2))

    assert any("nobody" in message for message in found)


def test_a_case_names_a_known_scenario():
    found = s23(http_case(mocks={"room-vendor": "nothing"}), http_case("h2", 2))

    assert any("nothing" in message for message in found)


def test_a_visible_case_names_visible_scenarios_only():
    hidden = http_case(visible=True, mocks={"room-vendor": "limited"})

    assert any("hidden" in message for message in s23(hidden, http_case("h2", 2)))


def test_a_hidden_case_may_name_a_hidden_scenario():
    assert s23(http_case(mocks={"room-vendor": "limited"}), http_case("h2", 2)) == []


def test_a_log_assertion_names_a_known_mock_server_and_route():
    unknown_mock = http_case(log=(LogAssertion("nobody", count=1),))
    unknown_route = http_case(log=(LogAssertion("room-vendor", route="nothing", count=1),))

    assert any("nobody" in message for message in s23(unknown_mock, http_case("h2", 2)))
    assert any("nothing" in message for message in s23(unknown_route, http_case("h2", 2)))


def test_waits_stay_within_the_cases_hang_guard():
    slow = http_case(mocks={"room-vendor": "sequenced"}, hang_guard_ms=8000)

    assert any("hang guard" in message for message in s23(slow, http_case("h2", 2)))


def test_a_problems_hang_guard_applies_to_a_case_with_none():
    limited = http_case(mocks={"room-vendor": "limited"})

    found = s23(limited, http_case("h2", 2), hang_guard_ms=2000)

    assert any("hang guard" in message for message in found)


def test_a_comparator_that_cannot_judge_a_body_is_refused():
    found = s23(*EVERY_LEVEL, comparator=ComparatorSpec(ComparatorType.OPS))

    assert any("cannot judge" in message for message in found)


def test_a_cases_own_comparator_overrides_the_problems():
    good = ComparatorSpec(ComparatorType.UNORDERED)
    cases = (http_case("h1", 1, comparator=good), http_case("h2", 2, comparator=good))

    assert s23(*cases, comparator=ComparatorSpec(ComparatorType.OPS)) == []


def test_fresh_with_data_needs_a_reset_command():
    project = service(services="c.yaml")

    found = s23(http_case(fresh=True), http_case("h2", 2), project=project)

    assert any("commands.reset" in message for message in found)


def test_fresh_with_no_data_only_restarts_and_needs_no_reset():
    assert s23(http_case(fresh=True), http_case("h2", 2)) == []


def steps_case(target: str) -> Case:
    step = HttpStep("step 1 GET", RequestTemplate("GET", target), HttpExpected(200))
    return Case("h1", HttpCaseInput({}, steps=(step,)), None, level=1)


def test_a_step_may_name_the_app_by_its_origin():
    assert s23(steps_case("http://app:8000/me"), http_case("h2", 2)) == []


def test_a_step_may_name_what_the_grader_reaches():
    project = service(services="c.yaml", grader_reach=("idp:8080", "room-vendor:8080"))
    cases = (steps_case("http://idp:8080/realms"), steps_case("http://room-vendor:8080/r"))

    assert s23(*cases, http_case("h2", 2), project=project) == []


def test_a_step_naming_a_mock_server_the_grader_does_not_reach_is_refused():
    found = s23(steps_case("http://room-vendor:8080/r"), http_case("h2", 2))

    assert any("http://room-vendor:8080 is no origin" in message for message in found)


def test_a_step_naming_an_undeclared_origin_is_refused():
    found = s23(steps_case("http://keycloak:8080/realms"), http_case("h2", 2))
    assert any("http://keycloak:8080 is no origin the problem declares" in item for item in found)
