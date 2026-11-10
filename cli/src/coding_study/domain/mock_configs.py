"""A problem's mock servers as its files hold them, and the one JSON document a stack mounts
(docs/specs/service-projects.md#mock-server).

The rendering is where hidden material stays out: a dev or test stack's document holds visible
scenarios only, and a `body_file` is inlined, so no other file of the problem reaches a container
and the body of a hidden scenario goes wherever that scenario goes.
"""

import json
import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from coding_study.domain.errors import ContentError, ContentIssue

API_SUFFIX = ".API.md"
"""`mocks/<name>.API.md`, next to `mocks/<name>.yaml`."""
BODY_FILE = "body_file"
BODY = "body"
OPENING = "{{"
_REFERENCE = (
    r"(?:request\.(?:method|path|body(?:\.[A-Za-z0-9_-]+)*"
    r"|query\.[A-Za-z0-9_-]+|headers\.[A-Za-z0-9-]+)|seq)"
)
RUN_TIME_VALUE = re.compile(rf"\{{\{{(?:(?:len|words|json)\({_REFERENCE}\)|{_REFERENCE})\}}\}}")
"""What a response may fill in per request (docs/specs/service-projects.md#run-time-values). The
mock server reads the same grammar in `adapters/mock_server/templates.py`, which runs alone and
cannot import this; `tests/mock_template_table.py` holds the two to one table."""
MILLISECONDS_PER_SECOND = 1000
RETRY_AFTER = "retry-after"
_RENDERED_FIELDS = ("upstream", "routes", "scenarios")

type _Document = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class MockFiles:
    """One mock server in the problem's own files."""

    document: _Document
    """Its config, valid against schemas/mock.schema.json."""
    bodies: Mapping[str, str | None] = field(default_factory=dict[str, str | None])
    """The text of each `body_file` the config names that exists, by that name; None for one that
    is not UTF-8 text."""
    api: str | None = None
    """`mocks/<name>.API.md`, the vendor's visible documentation; None when there is none."""


class ScenarioReach(StrEnum):
    """Which scenarios a stack's mock server may serve."""

    VISIBLE = "visible"
    """A dev or test stack."""
    EVERY = "every"
    """A graded stack."""


def scenario_documents(files: MockFiles) -> Mapping[str, _Document]:
    return cast(Mapping[str, _Document], files.document.get("scenarios", {}))


def scenario_names(files: MockFiles) -> tuple[str, ...]:
    return tuple(scenario_documents(files))


def visible_scenario_names(files: MockFiles) -> tuple[str, ...]:
    """A scenario is hidden unless it says otherwise, so a forgotten flag leaks nothing."""
    return tuple(
        name for name, scenario in scenario_documents(files).items() if scenario.get("visible")
    )


def route_documents(files: MockFiles) -> tuple[_Document, ...]:
    return tuple(cast(list[_Document], files.document.get("routes", [])))


def route_ids(files: MockFiles) -> tuple[str, ...]:
    return tuple(str(route["id"]) for route in route_documents(files))


def response_fields(files: MockFiles) -> Iterator[tuple[str, _Document]]:
    """Every place in the config that can hold a response's fields, with where it is. A route that
    passes through to an upstream holds none."""
    for route in route_documents(files):
        if "response" in route:
            yield f"routes.{route['id']}.response", cast(_Document, route["response"])
    for name, scenario in scenario_documents(files).items():
        for index, entry in enumerate(_entries(scenario)):
            yield f"scenarios.{name}[{index}]", entry


def response_texts(fields: _Document, files: MockFiles) -> Iterator[str]:
    """Every text of a response's fields that may name run-time values: each string of its body,
    or the text of its `body_file`."""
    yield from _json_strings(fields.get(BODY))
    body_file = fields.get(BODY_FILE)
    if isinstance(body_file, str):
        yield from _json_strings(files.bodies.get(body_file))


def malformed_run_time_value(text: str) -> str | None:
    """The first `{{` that opens no run-time value, from there to the end of the text, or None."""
    position = text.find(OPENING)
    while position != -1:
        found = RUN_TIME_VALUE.match(text, position)
        if found is None:
            return text[position:]
        position = text.find(OPENING, found.end())
    return None


def scenario_waits_ms(scenario: _Document) -> list[int]:
    """What each entry of a scenario makes the app wait: its delay, then what `Retry-After` asks."""
    return [_entry_wait_ms(entry) for entry in _entries(scenario)]


def rendered_mock_config(
    mocks: Mapping[str, MockFiles], control_token: str, reach: ScenarioReach
) -> str:
    """The document `adapters/mock_server` reads. Raises ContentError for a `body_file` that is not
    there or not text; S20 finds that first."""
    return json.dumps(
        {
            "control_token": control_token,
            "mocks": {name: _rendered(files, name, reach) for name, files in mocks.items()},
        },
        indent=1,
    )


def _rendered(files: MockFiles, name: str, reach: ScenarioReach) -> dict[str, object]:
    kept = _reachable(files, reach)
    document = {**files.document, "scenarios": kept}
    return {
        key: _inlined(document[key], files, name) for key in _RENDERED_FIELDS if key in document
    }


def _reachable(files: MockFiles, reach: ScenarioReach) -> dict[str, _Document]:
    if reach is ScenarioReach.EVERY:
        return dict(scenario_documents(files))
    visible = visible_scenario_names(files)
    return {name: scenario_documents(files)[name] for name in visible}


def _inlined(value: object, files: MockFiles, mock: str) -> object:
    if isinstance(value, list):
        return [_inlined(found, files, mock) for found in cast(list[object], value)]
    if not isinstance(value, Mapping):
        return value
    rendered: dict[str, object] = {}
    for key, found in cast(_Document, value).items():
        if key == BODY_FILE:
            rendered[BODY] = _body_text(found, files, mock)
        else:
            rendered[key] = found if key == BODY else _inlined(found, files, mock)
    return rendered


def _body_text(name: object, files: MockFiles, mock: str) -> str:
    text = files.bodies.get(str(name))
    if text is None:
        message = f"body_file {name} is not there, or is not UTF-8 text"
        raise ContentError([ContentIssue(f"mocks/{mock}", BODY_FILE, message)])
    return text


def _json_strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in cast(list[object], value):
            yield from _json_strings(item)
    elif isinstance(value, Mapping):
        for item in cast(_Document, value).values():
            yield from _json_strings(item)


def _entries(scenario: _Document) -> tuple[_Document, ...]:
    sequence = scenario.get("sequence")
    return tuple(cast(list[_Document], sequence)) if sequence is not None else (scenario,)


def _entry_wait_ms(entry: _Document) -> int:
    delay = cast(int, entry.get("delay_ms", 0))
    return delay + _retry_after_ms(cast(Mapping[str, str], entry.get("headers", {})))


def _retry_after_ms(headers: Mapping[str, str]) -> int:
    value = retry_after_text(headers) or ""
    return int(value) * MILLISECONDS_PER_SECOND if value.isdigit() else 0


def retry_after_text(headers: Mapping[str, str]) -> str | None:
    """The `Retry-After` of these headers, its name in any case."""
    return next((found for name, found in headers.items() if name.lower() == RETRY_AFTER), None)
