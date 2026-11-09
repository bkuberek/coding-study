"""oauth-pkce-client-typescript grades against a realm the problem imports into its identity
provider at each start. Its cases name that realm's client, user and grader by fixed ids, and the
starter's config names the client's registered URLs. These tests keep the realm, the manifest, the
compose file, the starter and the cases in step, and every change a case makes to the provider
undone by its cleanup, since the provider's state lasts the whole run."""

import json
import re
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0280-oauth-pkce-client-typescript"
REALM: Mapping[str, Any] = json.loads(
    (PROBLEM / "services" / "realm" / "campus-realm.json").read_text(encoding="utf-8")
)
PROJECT: Mapping[str, Any] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]
COMPOSE: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "services" / "compose.yaml").read_text(encoding="utf-8")
)
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
CONFIG = (PROBLEM / "starter" / "src" / "config.ts").read_text(encoding="utf-8")
CLIENTS = {client["clientId"]: client for client in REALM["clients"]}
PORTAL = CLIENTS[PROJECT["env"]["OIDC_CLIENT_ID"]]
LEARNER = next(user for user in REALM["users"] if user["username"] == "learner")
ADMIN_ROOT = "http://idp:8080/admin/realms/"
CHANGES = frozenset({"POST", "PUT"})
"""What a case may change the provider with: each needs a cleanup step."""


def config_value(name: str) -> str:
    found = re.search(rf'export const {name} = "([^"]+)";', CONFIG)
    assert found is not None, f"src/config.ts names no {name}"
    return found[1]


def requests_of(steps: list[Mapping[str, Any]]) -> Iterator[Mapping[str, Any]]:
    """Each request of the steps, with the flows they use written out."""
    for step in steps:
        if "use" in step:
            yield from requests_of(TESTS["flows"][step["use"]])
        else:
            yield step["request"]


def every_request() -> Iterator[Mapping[str, Any]]:
    for case in TESTS["cases"]:
        yield from requests_of(case["steps"])
        yield from requests_of(case.get("cleanup", []))


def admin_changes(case: Mapping[str, Any]) -> list[str]:
    """The admin calls of a case that change the provider, apart from ending the user's sessions,
    which every case starts afresh anyway."""
    return [
        request["url"]
        for request in requests_of(case["steps"])
        if request.get("url", "").startswith(ADMIN_ROOT)
        and request["method"] in CHANGES
        and not request["url"].endswith("/logout")
    ]


def test_the_issuer_is_the_realm_at_the_name_keycloak_writes_its_urls_with():
    command = COMPOSE["services"]["keycloak"]["command"]
    hostname = next(word for word in command if word.startswith("--hostname="))

    assert PROJECT["env"]["OIDC_ISSUER"] == f"{hostname.partition('=')[2]}/realms/{REALM['realm']}"


def test_the_healthcheck_asks_for_the_realms_own_discovery_document():
    probe = COMPOSE["services"]["keycloak"]["healthcheck"]["test"][-1]

    assert f"/realms/{REALM['realm']}/.well-known/openid-configuration" in probe


def test_the_callback_the_starter_sends_is_the_one_the_realm_registered():
    assert PORTAL["redirectUris"] == [config_value("REDIRECT_URI")]


def test_the_logout_redirect_the_starter_sends_is_the_one_the_realm_registered():
    registered = PORTAL["attributes"]["post.logout.redirect.uris"]

    assert registered == config_value("POST_LOGOUT_REDIRECT_URI")


@pytest.mark.parametrize(
    ("setting", "value"),
    [("publicClient", True), ("standardFlowEnabled", True), ("directAccessGrantsEnabled", False)],
)
def test_the_portal_is_a_public_client_of_the_code_flow_only(setting: str, value: bool):
    assert PORTAL[setting] is value


def test_the_realm_requires_pkce_with_s256():
    assert PORTAL["attributes"]["pkce.code.challenge.method"] == "S256"


@pytest.mark.parametrize(
    ("setting", "value"), [("revokeRefreshToken", True), ("refreshTokenMaxReuse", 0)]
)
def test_the_realm_rotates_refresh_tokens_and_refuses_a_spent_one(setting: str, value: object):
    assert REALM[setting] == value


def test_the_lifespan_a_case_restores_is_the_one_the_realm_starts_with():
    restored = [
        request["json"]["attributes"]["access.token.lifespan"]
        for case in TESTS["cases"]
        for request in requests_of(case.get("cleanup", []))
        if request["method"] == "PUT"
    ]

    assert set(restored) == {PORTAL["attributes"]["access.token.lifespan"]}


def me_bodies() -> list[object]:
    """Each body a case expects of `GET /me`."""
    return [
        step["expected"]["body"]
        for case in TESTS["cases"]
        for step in case["steps"]
        if step.get("request", {}).get("path") == "/me" and "body" in step.get("expected", {})
    ]


def test_some_case_says_who_me_answers():
    assert me_bodies()


def test_the_user_me_answers_is_the_realms_learner():
    expected = {"sub": LEARNER["id"], "username": "learner", "email": LEARNER["email"]}

    assert all(body == expected for body in me_bodies())


def test_the_admin_api_names_only_the_realms_own_client_and_user():
    known = {PORTAL["id"], LEARNER["id"]}
    named = {
        found
        for request in every_request()
        for found in re.findall(r"/(?:clients|users)/([0-9a-f-]{36})", request.get("url", ""))
    }

    assert named <= known


def test_the_grader_logs_in_as_the_realms_grader_client():
    grader = CLIENTS["grader"]
    sent = TESTS["flows"]["admin"][0]["request"]["form"]

    assert (sent["client_id"], sent["client_secret"]) == ("grader", grader["secret"])


def test_the_grader_client_carries_the_admin_apis_audience():
    assert "kc-admin-api" in CLIENTS["grader"]["defaultClientScopes"]


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=case["id"]) for case in TESTS["cases"] if admin_changes(case)],
)
def test_a_case_that_changes_the_provider_undoes_it_in_cleanup(case: Mapping[str, Any]):
    assert len(case.get("cleanup", [])) == len(admin_changes(case))
