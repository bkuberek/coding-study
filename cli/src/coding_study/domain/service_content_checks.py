"""`cstudy verify --static` on what a service project trusts beside its manifest: S20 on its mock
configs, S21 and S22 on its compose file, and S23 on its HTTP cases
(docs/specs/service-projects.md#static). Each issue comes back as where it is and what is wrong.

A compose file belongs to a format `cstudy` does not own, so S21 lists what the core keeps for
itself instead of describing the whole file.
"""

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from coding_study.domain.cases import Case
from coding_study.domain.http_case import HttpCaseInput
from coding_study.domain.http_grading import HTTP_COMPARATORS
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
from coding_study.domain.sandbox import RESERVED_SERVICES
from coding_study.domain.service_project import ServiceMock, ServiceProject

MOCKS_DIRECTORY = "mocks/"
MAX_WAIT_S = 3
"""What a scenario may make an app wait, so a hidden case stays under the 10 s hang guard."""
VENDOR_DOCUMENT = "vendors/{name}/API.md"
_PINNED_IMAGE = re.compile(r"[^@\s]+@sha256:[0-9a-f]+")
_REPOSITORY = re.compile(r"(?:.*/)?(?P<name>[^/:@]+)(?::[^@/]*)?(?:@.*)?$")
_THE_CORES_FIELDS = (
    "ports",
    "networks",
    "network_mode",
    "restart",
    "container_name",
    "privileged",
    "cap_add",
)
_REQUIRED_FIELDS = ("mem_limit", "pids_limit", "healthcheck")
_TOP_LEVEL_FIELDS = frozenset({"services", "volumes"})
_DOCKER_SOCKET = "docker.sock"
_CURRENT_FOLDER = "./"
_VOLUME_SEPARATOR = ":"

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


def compose_issues(service: ServiceProject, document: object) -> _Found:
    """S21, and S22's part on the compose file. `document` is the parsed `project.services`."""
    if not isinstance(document, Mapping):
        yield "", "a compose file is a mapping with services"
        return
    compose = cast(_Document, document)
    for field in compose:
        if field not in _TOP_LEVEL_FIELDS:
            yield str(field), "a compose file holds only services and their volumes"
    yield from _external_volumes(compose)
    services = cast(_Document, compose.get("services") or {})
    mock_names = {mock.name for mock in service.mocks}
    for name, found in services.items():
        yield from _compose_service(name, cast(_Document, found), mock_names)
    yield from _repositories(service, services)


def _external_volumes(compose: _Document) -> _Found:
    for name, volume in cast(_Document, compose.get("volumes") or {}).items():
        if isinstance(volume, Mapping) and cast(_Document, volume).get("external"):
            yield f"volumes.{name}", "an external volume outlives what cstudy can remove"


def _compose_service(name: str, service: _Document, mock_names: set[str]) -> _Found:
    where = f"services.{name}"
    if name in RESERVED_SERVICES:
        yield where, f'"{name}" is a reserved name'
    if name in mock_names:
        yield where, f'"{name}" is the name of a mock server'
    if "build" in service:
        yield f"{where}.build", "a build is refused: nothing is built, so name an image"
    if not _PINNED_IMAGE.fullmatch(str(service.get("image", ""))):
        yield f"{where}.image", f'"{service.get("image")}" is not pinned by digest'
    for field in _THE_CORES_FIELDS:
        if field in service:
            yield f"{where}.{field}", f"{field} is cstudy's to set"
    for field in _REQUIRED_FIELDS:
        if field not in service:
            yield f"{where}.{field}", f"{field} is required"
    for volume in cast(Sequence[object], service.get("volumes") or ()):
        yield from _volume(where, volume)


def _volume(where: str, volume: object) -> _Found:
    location = f"{where}.volumes"
    source, is_bind = _volume_source(volume)
    if source is None:
        yield location, "an anonymous volume carries no label, so use a named one"
    elif _DOCKER_SOCKET in source:
        yield location, "the Docker socket is never mounted"
    elif is_bind and relative_path_issue(source.removeprefix(_CURRENT_FOLDER)) is not None:
        yield location, f"the bind mount {source} is outside the problem"


def _volume_source(volume: object) -> tuple[str | None, bool]:
    """What a volume entry mounts, and whether that is a path on this machine."""
    if isinstance(volume, Mapping):
        entry = cast(_Document, volume)
        source = entry.get("source")
        return (str(source) if source is not None else None), entry.get("type") == "bind"
    source, separator, _target = str(volume).partition(_VOLUME_SEPARATOR)
    if not separator:
        return None, False
    return source, source.startswith((".", "/", "~"))


def _repositories(service: ServiceProject, services: _Document) -> _Found:
    named = {
        found["name"]
        for entry in services.values()
        if (found := _REPOSITORY.match(str(cast(_Document, entry).get("image", ""))))
    }
    declared = set(service.requires.services)
    for name in sorted(named - declared):
        yield "project.requires.services", f"must name {name}, an image of the compose file"
    for name in sorted(declared - named):
        yield "project.requires.services", f"names {name}, which no image of the compose file is"


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
