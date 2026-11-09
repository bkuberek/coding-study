import base64
import json
from typing import Any

from coding_study.adapters.mock_server.config import JwtTamper, TamperKind
from coding_study.adapters.mock_server.jwt_tamper import tampered_body


def segment(document: dict[str, Any]) -> str:
    raw = json.dumps(document, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decoded(part: str) -> Any:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


HEADER = segment({"alg": "RS256", "typ": "JWT", "kid": "key-1"})
PAYLOAD = segment({"sub": "learner", "nonce": "n-1"})
SIGNATURE = "Abc_def-123"
TOKEN = f"{HEADER}.{PAYLOAD}.{SIGNATURE}"
TOKEN_ANSWER = {"access_token": "at", "id_token": TOKEN, "expires_in": 300}


def tampered(document: Any, tamper: JwtTamper) -> Any:
    return json.loads(tampered_body(json.dumps(document).encode(), tamper))


def test_alg_none_replaces_the_header_and_drops_the_signature():
    token = tampered(TOKEN_ANSWER, JwtTamper(("id_token",), TamperKind.ALG_NONE))["id_token"]
    header, payload, signature = token.split(".")
    assert (decoded(header), payload, signature) == ({"alg": "none"}, PAYLOAD, "")


def test_bad_signature_changes_the_first_character_of_the_signature_only():
    tamper = JwtTamper(("id_token",), TamperKind.BAD_SIGNATURE)
    token = tampered(TOKEN_ANSWER, tamper)["id_token"]
    assert token == f"{HEADER}.{PAYLOAD}.Bbc_def-123"


def test_a_signature_that_starts_with_the_replacement_gets_another_character():
    answer = {"id_token": f"{HEADER}.{PAYLOAD}.Axyz"}
    token = tampered(answer, JwtTamper(("id_token",), TamperKind.BAD_SIGNATURE))["id_token"]
    assert token.rsplit(".", 1)[1] == "Bxyz"


def test_the_other_fields_of_the_answer_stay_as_they_were():
    answer = tampered(TOKEN_ANSWER, JwtTamper(("id_token",), TamperKind.ALG_NONE))
    assert {name: answer[name] for name in ("access_token", "expires_in")} == {
        "access_token": "at",
        "expires_in": 300,
    }


def test_a_dotted_field_reaches_into_nested_objects():
    answer = {"tokens": {"id": TOKEN}}
    token = tampered(answer, JwtTamper(("tokens", "id"), TamperKind.ALG_NONE))["tokens"]["id"]
    assert token.endswith(f".{PAYLOAD}.")


def test_a_body_without_that_field_goes_out_unchanged():
    body = json.dumps({"access_token": "at"}).encode()
    assert tampered_body(body, JwtTamper(("id_token",), TamperKind.ALG_NONE)) == body


def test_a_field_that_is_not_a_jwt_goes_out_unchanged():
    body = json.dumps({"id_token": "opaque"}).encode()
    assert tampered_body(body, JwtTamper(("id_token",), TamperKind.ALG_NONE)) == body


def test_a_body_that_is_not_json_goes_out_unchanged():
    assert tampered_body(b"<html>", JwtTamper(("id_token",), TamperKind.ALG_NONE)) == b"<html>"
