"""`cstudy verify --static` on what a service project trusts beside its manifest: S20 on its mock
configs, S21 and S22 on its compose file, the names in its manifest that only that file settles, and
S23 on its HTTP cases (docs/specs/service-projects.md#static). Each issue comes back as where it is
and what is wrong.

A compose file belongs to a format `cstudy` does not own, so S21 allows a short list of what a
backing service may set, `BACKING_SERVICE_FIELDS`, and refuses the rest: a field that compose adds
later is refused until someone looks at it. A stack holds a file to S21 before it starts.
"""

import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from coding_study.domain.cases import Case
from coding_study.domain.http_case import HttpCaseInput
from coding_study.domain.http_case_checks import step_issues
from coding_study.domain.http_grading import HTTP_COMPARATORS
from coding_study.domain.http_origins import declared_origins
from coding_study.domain.mock_configs import (
    API_SUFFIX,
    BODY_FILE,
    MILLISECONDS_PER_SECOND,
    MockFiles,
    response_fields,
    retry_after_text,
    route_ids,
    scenario_documents,
    scenario_names,
    scenario_waits_ms,
    visible_scenario_names,
)
from coding_study.domain.precedence import DEFAULT_HANG_GUARD_MS
from coding_study.domain.problem import ComparatorSpec, Level
from coding_study.domain.project import ProjectFiles, relative_path_issue
from coding_study.domain.sandbox import (
    BACKING_SERVICE_FIELDS,
    MOCK_PORT,
    RESERVED_SERVICES,
    RESERVED_VOLUMES,
    backing_services_of,
    volume_source,
)
from coding_study.domain.service_checks import THIS_MACHINE, url_host
from coding_study.domain.service_project import ServiceMock, ServiceProject

MOCKS_DIRECTORY = "mocks/"
MAX_WAIT_S = 3
"""What a scenario may make an app wait, so a hidden case stays under the 10 s hang guard."""
VENDOR_DOCUMENT = "vendors/{name}/API.md"
_PINNED_IMAGE = re.compile(r"[^@\s]+@sha256:[0-9a-f]+")
_REPOSITORY = re.compile(r"(?:.*/)?(?P<name>[^/:@]+)(?::[^@/]*)?(?:@.*)?$")
_SERVICE_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
"""What the app reaches a service by, as a host name: lowercase letters, digits and `-`."""
_MEMORY_LIMIT = re.compile(r"[1-9][0-9]*[bkmg]?")
_THE_CORES_FIELDS = frozenset(
    {
        "ports",
        "networks",
        "network_mode",
        "container_name",
        "labels",
        "logging",
        "cap_drop",
        "security_opt",
    }
)
_ALLOWED_FIELDS = ", ".join(sorted(BACKING_SERVICE_FIELDS))
_REQUIRED_FIELDS = ("mem_limit", "pids_limit", "healthcheck")
_TOP_LEVEL_FIELDS = frozenset({"services", "volumes"})
_MOUNT_TYPES = frozenset({"bind", "volume", "tmpfs"})
_TMPFS = "tmpfs"
_NO_CHECK = "NONE"
_DOCKER_SOCKET = "docker.sock"
_CURRENT_FOLDER = "./"
_GRADER_REACH = "project.grader_reach"
_NO_COMPOSE: Mapping[str, object] = {}

type _Found = Iterator[tuple[str, str]]
type _Document = Mapping[str, object]


def mock_config_issues(service: ServiceProject, files: ProjectFiles) -> _Found:
    """S20; the schema's part already refused a config when the problem was loaded."""
    for mock in service.mocks:
        if not mock.config.startswith(MOCKS_DIRECTORY):
            yield mock.config, f"a mock config lies in {MOCKS_DIRECTORY}"
        found = files.mocks.get(mock.name)
        if found is not None:
            yield from _bodies(mock, found)
            yield from _waits(mock, found)
            yield from _documentation(mock, found, files)
            yield from _upstream(mock, found, files)


def _upstream(mock: ServiceMock, found: MockFiles, files: ProjectFiles) -> _Found:
    """A pass-through reaches its upstream over `sandbox`, which has no way out, so the upstream is
    one of the backing services that share it with the mock server."""
    upstream = found.document.get("upstream")
    if upstream is None:
        return
    host = url_host(str(upstream))
    if host not in backing_services_of(files.backing_services or _NO_COMPOSE):
        yield mock.config, f"upstream: {host} is no service of the compose file"


def _bodies(mock: ServiceMock, files: MockFiles) -> _Found:
    for where, fields in response_fields(files):
        name = fields.get(BODY_FILE)
        if not isinstance(name, str):
            continue
        location = f"{mock.config} {where}"
        issue = relative_path_issue(name)
        if issue is not None:
            yield location, f"body_file {name} {issue}"
        elif name not in files.bodies:
            yield location, f"body_file {name} is not there"
        elif files.bodies[name] is None:
            yield location, f"body_file {name} is not UTF-8 text"


def _waits(mock: ServiceMock, files: MockFiles) -> _Found:
    for where, fields in response_fields(files):
        location = f"{mock.config} {where}"
        delay = fields.get("delay_ms", 0)
        if isinstance(delay, int) and delay > MAX_WAIT_S * MILLISECONDS_PER_SECOND:
            yield location, f"delay_ms is {delay}: a wait is at most {MAX_WAIT_S} s"
        text = retry_after_text(cast(Mapping[str, str], fields.get("headers", {})))
        if text is None:
            continue
        if not text.isdigit():
            yield location, f"Retry-After is given in whole seconds, not {text}"
        elif int(text) > MAX_WAIT_S:
            yield location, f"Retry-After is {text}: a wait is at most {MAX_WAIT_S} s"


def _documentation(mock: ServiceMock, found: MockFiles, files: ProjectFiles) -> _Found:
    document = mock.config.rpartition(".")[0] + API_SUFFIX
    api = found.api
    if api is None:
        yield document, f"{document} is missing: it is the vendor's visible documentation"
        return
    starter_path = VENDOR_DOCUMENT.format(name=mock.name)
    starter = files.starter.file(starter_path) if files.starter is not None else None
    if starter is None:
        yield f"starter/{starter_path}", f"missing: a copy of {document}"
    elif starter.text != api:
        yield f"starter/{starter_path}", f"must be byte for byte the same as {document}"
    visible = visible_scenario_names(found)
    for name in visible:
        if not _names(api, name):
            yield document, f"must list the visible scenario {name}"
    for name in scenario_names(found):
        if name not in visible and _names(api, name):
            yield document, f"must not name the hidden scenario {name}"


def _names(text: str, name: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text) is not None


@dataclass(frozen=True, slots=True)
class _ComposeNames:
    """What a service of the file may name: none of the mock servers, and only the file's own
    services and volumes."""

    mocks: frozenset[str]
    services: frozenset[str]
    volumes: frozenset[str]


def compose_issues(service: ServiceProject, document: object) -> _Found:
    """S21: nothing in the problem's compose file reaches past the sandbox. `document` is the
    parsed `project.services`."""
    if not isinstance(document, Mapping):
        yield "", "a compose file is a mapping with services"
        return
    compose = cast(_Document, document)
    for field in compose:
        if field not in _TOP_LEVEL_FIELDS:
            yield str(field), f"{field} is refused: a compose file holds services and volumes"
    volumes = cast(_Document, compose.get("volumes") or {})
    yield from _volumes(volumes)
    services = backing_services_of(compose)
    if not services:
        yield "services", "a compose file names at least one service"
    names = _ComposeNames(
        frozenset(mock.name for mock in service.mocks), frozenset(services), frozenset(volumes)
    )
    for name, found in services.items():
        yield from _compose_service(name, found, names)


def _volumes(volumes: _Document) -> _Found:
    """A problem's volume carries `cstudy`'s labels and nothing of its own: a driver or its options
    can mount a path of this machine, a name can take another stack's, and an external volume
    outlives what cstudy can remove."""
    for name, volume in volumes.items():
        where = f"volumes.{name}"
        if name in RESERVED_VOLUMES:
            yield where, f'"{name}" is reserved: it is a volume of the stack\'s own'
        if isinstance(volume, Mapping) and cast(_Document, volume).get("external"):
            yield where, "an external volume outlives what cstudy can remove"
        elif volume:
            yield where, "a volume takes no settings: cstudy names and labels it"


def _compose_service(name: str, service: _Document, names: _ComposeNames) -> _Found:
    where = f"services.{name}"
    if name in RESERVED_SERVICES:
        yield where, f'"{name}" is a reserved name'
    elif not _SERVICE_NAME.fullmatch(name):
        yield where, f'"{name}" is no name the app can reach: lowercase letters, digits and -'
    if name in names.mocks:
        yield where, f'"{name}" is the name of a mock server'
    yield from _fields(where, service)
    if not _PINNED_IMAGE.fullmatch(str(service.get("image", ""))):
        yield f"{where}.image", f'"{service.get("image")}" is not pinned by digest'
    for field in _REQUIRED_FIELDS:
        if field not in service:
            yield f"{where}.{field}", f"{field} is required"
    yield from _limits(where, service)
    for volume in cast(Sequence[object], service.get("volumes") or ()):
        yield from _volume(where, volume, names.volumes)
    for other in _waits_for(service):
        if other not in names.services:
            yield f"{where}.depends_on", f"{other} is not a backing service of this file"


def _fields(where: str, service: _Document) -> _Found:
    for field in service:
        if field in _THE_CORES_FIELDS:
            yield f"{where}.{field}", f"{field} is cstudy's to set"
        elif field == "build":
            yield f"{where}.build", "a build is refused: nothing is built, so name an image"
        elif field not in BACKING_SERVICE_FIELDS:
            yield f"{where}.{field}", f"{field} is not allowed: a service sets {_ALLOWED_FIELDS}"


def _limits(where: str, service: _Document) -> _Found:
    pids = service.get("pids_limit")
    if "pids_limit" in service and not (type(pids) is int and pids > 0):
        yield f"{where}.pids_limit", f"pids_limit is a positive number, not {pids}"
    memory = service.get("mem_limit")
    if "mem_limit" in service and not _MEMORY_LIMIT.fullmatch(str(memory)):
        yield f"{where}.mem_limit", f'mem_limit is a size such as "256m", not {memory}'
    check = service.get("healthcheck")
    if "healthcheck" in service and not _checks_something(check):
        yield f"{where}.healthcheck", "a healthcheck with a test is what says the service is ready"


def _checks_something(check: object) -> bool:
    if not isinstance(check, Mapping):
        return False
    found = cast(_Document, check)
    test = found.get("test")
    words: list[object] = cast(list[object], test) if isinstance(test, list) else [test]
    return bool(words) and words[0] not in (None, "", _NO_CHECK) and not found.get("disable")


def _volume(where: str, volume: object, declared: frozenset[str]) -> _Found:
    location = f"{where}.volumes"
    long_form = cast(_Document, volume) if isinstance(volume, Mapping) else None
    kind = long_form.get("type") if long_form is not None else None
    if long_form is not None and kind not in _MOUNT_TYPES:
        yield location, f"a mount of type {kind} is refused: bind, volume or tmpfs"
        return
    if kind == _TMPFS:
        return
    source, is_bind = volume_source(cast(object, volume))
    if source is None:
        yield location, "an anonymous volume carries no label, so use a named one"
    elif _DOCKER_SOCKET in source:
        yield location, "the Docker socket is never mounted"
    elif is_bind and relative_path_issue(source.removeprefix(_CURRENT_FOLDER)) is not None:
        yield location, f"the bind mount {source} is outside the problem"
    elif not is_bind and source not in declared:
        yield location, f"the volume {source} is not one the file declares under volumes"


def _waits_for(service: _Document) -> tuple[str, ...]:
    found = service.get("depends_on")
    if isinstance(found, Mapping | list):
        return tuple(str(name) for name in cast(Iterable[object], found))
    return () if found is None else (str(found),)


def compose_requires_issues(service: ServiceProject, document: object) -> _Found:
    """S22's part on the compose file: `requires.services` names the images' repositories."""
    if not isinstance(document, Mapping):
        return
    named = {
        found["name"]
        for entry in backing_services_of(cast(_Document, document)).values()
        if (found := _REPOSITORY.match(str(entry.get("image", ""))))
    }
    declared = set(service.requires.services)
    for name in sorted(named - declared):
        yield "project.requires.services", f"must name {name}, an image of the compose file"
    for name in sorted(declared - named):
        yield "project.requires.services", f"names {name}, which no image of the compose file is"


def manifest_name_issues(service: ServiceProject, document: object) -> _Found:
    """S19's rules on what `meta.yaml` names that only the compose file settles: a URL in `env`
    names a mock server or a service of the file, and the grader reaches only those. `document` is
    the parsed `project.services`, or None without one."""
    compose = cast(_Document, document) if isinstance(document, Mapping) else _NO_COMPOSE
    services = backing_services_of(compose)
    mocks = {mock.name for mock in service.mocks}
    if service.services is not None:
        for name, value in service.env.items():
            host = url_host(value)
            if host is not None and host not in (*mocks, *services, *THIS_MACHINE):
                yield f"project.env.{name}", f"{host} is neither a mock server nor a service"
    for origin in service.grader_reach:
        name, _, port = origin.rpartition(":")
        if name in RESERVED_SERVICES:
            yield _GRADER_REACH, f'"{name}" is reserved: the grader reaches your app at its URL'
        elif name in mocks and port != str(MOCK_PORT):
            yield _GRADER_REACH, f"the mock server {name} answers on port {MOCK_PORT}"
        elif name not in mocks and name not in services:
            yield _GRADER_REACH, f"{name} is neither a backing service nor a mock server"


@dataclass(frozen=True, slots=True)
class _CaseRules:
    files: ProjectFiles
    service: ServiceProject
    comparator: ComparatorSpec
    hang_guard_ms: int | None
    level_count: int


def http_case_issues(
    cases: Sequence[Case],
    files: ProjectFiles,
    service: ServiceProject,
    *,
    levels: Sequence[Level],
    comparator: ComparatorSpec,
    hang_guard_ms: int | None,
) -> _Found:
    """S23, and S10 for a problem with no methods to number its levels by."""
    numbers = [level.number for level in levels]
    if numbers != list(range(1, len(numbers) + 1)):
        yield "levels", "levels must be numbered 1, 2, ... without gaps"
    rules = _CaseRules(files, service, comparator, hang_guard_ms, len(numbers))
    for index, case in enumerate(cases):
        yield from _case(f"cases[{index}] {case.id}", case, rules)
    with_cases = {case.level for case in cases}
    for number in numbers:
        if number not in with_cases:
            yield "levels", f"level {number} has no cases"


def _case(where: str, case: Case, rules: _CaseRules) -> _Found:
    if case.level is None or not 1 <= case.level <= rules.level_count:
        yield where, f"level must be from 1 to {rules.level_count}"
    http = case.input
    if not isinstance(http, HttpCaseInput):
        yield where, "a service project's case needs a request"
        return
    used = http.comparator or rules.comparator
    if used.type not in HTTP_COMPARATORS:
        yield where, f"the comparator {used.type} cannot judge a response body"
    yield from _scenarios(where, case, http, rules)
    yield from _logs(where, http, rules)
    origins = declared_origins(rules.service.app.port, rules.service.grader_reach)
    for message in step_issues(http, origins):
        yield where, message
    if http.fresh and rules.service.services is not None and rules.service.commands.reset is None:
        yield where, "fresh with data needs commands.reset"


def _scenarios(where: str, case: Case, http: HttpCaseInput, rules: _CaseRules) -> _Found:
    limit = case.hang_guard_ms or rules.hang_guard_ms or DEFAULT_HANG_GUARD_MS
    for mock, scenario in http.mocks.items():
        files = rules.files.mocks.get(mock)
        if files is None:
            yield where, f"no mock server named {mock}"
        elif scenario not in scenario_names(files):
            yield where, f"{mock} has no scenario {scenario}"
        else:
            if case.visible and scenario not in visible_scenario_names(files):
                yield where, f"a visible case cannot set the hidden scenario {scenario}"
            waits = sum(scenario_waits_ms(scenario_documents(files)[scenario]))
            if waits >= limit:
                yield where, f"{scenario} waits {waits} ms, past the hang guard of {limit} ms"


def _logs(where: str, http: HttpCaseInput, rules: _CaseRules) -> _Found:
    for assertion in http.log:
        files = rules.files.mocks.get(assertion.mock)
        if files is None:
            yield where, f"no mock server named {assertion.mock}"
        elif assertion.route is not None and assertion.route not in route_ids(files):
            yield where, f"{assertion.mock} has no route {assertion.route}"
