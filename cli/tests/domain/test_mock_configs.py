"""What a stack's mock server is handed: the configs on one JSON document, hidden scenarios only
when the stack grades."""

import json

import pytest

from coding_study.domain.errors import ContentError
from coding_study.domain.mock_configs import (
    MockFiles,
    ScenarioReach,
    rendered_mock_config,
    route_ids,
    scenario_names,
    scenario_waits_ms,
    visible_scenario_names,
)


def vendor(**scenarios: object) -> MockFiles:
    return MockFiles(
        {
            "routes": [
                {
                    "id": "rooms",
                    "method": "GET",
                    "path": "/rooms",
                    "response": {"status": 200, "body_file": "bodies/rooms.json"},
                }
            ],
            "scenarios": scenarios,
        },
        {"bodies/rooms.json": '{"rooms": []}\n', "bodies/secret.json": '"hidden"'},
    )


def rendered(mocks: dict[str, MockFiles], reach: ScenarioReach) -> dict:
    return json.loads(rendered_mock_config(mocks, "the-token", reach))


def test_the_rendering_holds_the_token_and_every_mock_server_by_name():
    document = rendered({"a": vendor(), "b": vendor()}, ScenarioReach.EVERY)

    assert document["control_token"] == "the-token"
    assert sorted(document["mocks"]) == ["a", "b"]


def test_a_practice_stack_never_gets_a_hidden_scenario():
    mocks = {"a": vendor(open={"visible": True, "status": 503}, hidden={"status": 429})}

    assert list(rendered(mocks, ScenarioReach.VISIBLE)["mocks"]["a"]["scenarios"]) == ["open"]


def test_a_scenario_with_no_visible_flag_is_hidden():
    mocks = {"a": vendor(forgotten={"status": 503})}

    assert rendered(mocks, ScenarioReach.VISIBLE)["mocks"]["a"]["scenarios"] == {}


def test_a_graded_stack_gets_every_scenario():
    mocks = {"a": vendor(open={"visible": True, "status": 503}, hidden={"status": 429})}

    assert sorted(rendered(mocks, ScenarioReach.EVERY)["mocks"]["a"]["scenarios"]) == [
        "hidden",
        "open",
    ]


def test_a_body_file_is_inlined_so_no_other_file_reaches_the_container():
    route = rendered({"a": vendor()}, ScenarioReach.EVERY)["mocks"]["a"]["routes"][0]

    assert route["response"] == {"status": 200, "body": '{"rooms": []}\n'}


def test_a_body_file_in_a_scenario_and_a_sequence_is_inlined():
    mocks = {
        "a": vendor(
            one={"body_file": "bodies/rooms.json"},
            many={"sequence": [{"status": 429}, {"status": 200, "body_file": "bodies/rooms.json"}]},
        )
    }

    scenarios = rendered(mocks, ScenarioReach.EVERY)["mocks"]["a"]["scenarios"]

    assert scenarios["one"]["body"] == '{"rooms": []}\n'
    assert scenarios["many"]["sequence"][1]["body"] == '{"rooms": []}\n'


def test_the_body_of_a_hidden_scenario_stays_out_of_a_practice_stack():
    mocks = {"a": vendor(hidden={"body_file": "bodies/secret.json"})}

    text = rendered_mock_config(mocks, "t", ScenarioReach.VISIBLE)

    assert "hidden" not in text


def test_a_body_file_that_is_not_there_is_a_content_error():
    mocks = {"a": vendor(broken={"visible": True, "body_file": "bodies/gone.json"})}

    with pytest.raises(ContentError, match=r"gone\.json"):
        rendered_mock_config(mocks, "t", ScenarioReach.VISIBLE)


def test_a_body_that_mentions_body_file_is_sent_as_it_is():
    mocks = {"a": vendor(literal={"body": {"body_file": "bodies/gone.json"}})}

    scenarios = rendered(mocks, ScenarioReach.EVERY)["mocks"]["a"]["scenarios"]

    assert scenarios["literal"]["body"] == {"body_file": "bodies/gone.json"}


def test_a_config_with_no_scenarios_renders_with_none():
    mocks = {"a": MockFiles({"routes": []})}

    assert rendered(mocks, ScenarioReach.EVERY)["mocks"]["a"] == {"routes": [], "scenarios": {}}


def test_names_and_routes_read_from_a_config():
    files = vendor(open={"visible": True, "status": 503}, hidden={"status": 429})

    assert scenario_names(files) == ("open", "hidden")
    assert visible_scenario_names(files) == ("open",)
    assert route_ids(files) == ("rooms",)


@pytest.mark.parametrize(
    ("scenario", "waits"),
    [
        ({"status": 503}, [0]),
        ({"delay_ms": 2000}, [2000]),
        ({"status": 429, "headers": {"Retry-After": "2"}}, [2000]),
        ({"status": 429, "headers": {"retry-after": "1"}, "delay_ms": 500}, [1500]),
        ({"sequence": [{"status": 429, "headers": {"Retry-After": "1"}}, {"delay_ms": 300}]},
         [1000, 300]),
    ],
)  # fmt: skip
def test_the_waits_of_a_scenario_are_each_entrys_delay_and_retry_after(scenario, waits):
    assert scenario_waits_ms(scenario) == waits


def test_a_retry_after_that_is_no_number_is_no_wait():
    assert scenario_waits_ms({"headers": {"Retry-After": "Wed, 21 Oct"}}) == [0]
