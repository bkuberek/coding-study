"""Spoiling a JWT inside a JSON answer, for a case that an app must refuse: base64url and JSON only,
with no key, so the mock server never signs anything (ADR 0019, R34).

A body that holds no JWT at the named field goes out unchanged. A case that relies on the tamper
then fails for the reference too, which is how `verify` finds the mistake in the config.
"""

import base64
import binascii
import json
from typing import cast

from .config import JwtTamper, TamperKind

JWT_PARTS = 3
NO_ALGORITHM_HEADER = {"alg": "none"}
REPLACEMENT_CHARACTERS = ("A", "B")
"""The first character of a spoiled signature becomes the first of these that differs from it, so
the signature's first six bits change, unlike its last character's, which may be padding."""


def tampered_body(body: bytes, tamper: JwtTamper) -> bytes:
    try:
        document: object = json.loads(body)
    except (ValueError, RecursionError):
        return body
    *parents, name = tamper.field
    holder = _object_at(document, tuple(parents))
    token = holder.get(name) if holder is not None else None
    if holder is None or not isinstance(token, str) or not _is_jwt(token):
        return body
    holder[name] = _tampered(token, tamper.kind)
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")).encode()


def _object_at(document: object, path: tuple[str, ...]) -> dict[str, object] | None:
    found = document
    for name in path:
        if not isinstance(found, dict):
            return None
        found = cast(dict[str, object], found).get(name)
    return cast(dict[str, object], found) if isinstance(found, dict) else None


def _is_jwt(token: str) -> bool:
    parts = token.split(".")
    if len(parts) != JWT_PARTS:
        return False
    try:
        json.loads(_decoded(parts[0]))
    except (ValueError, binascii.Error):
        return False
    return True


def _tampered(token: str, kind: TamperKind) -> str:
    header, payload, signature = token.split(".")
    match kind:
        case TamperKind.ALG_NONE:
            return f"{_encoded(json.dumps(NO_ALGORITHM_HEADER, separators=(',', ':')))}.{payload}."
        case TamperKind.BAD_SIGNATURE:
            return f"{header}.{payload}.{_spoiled(signature)}"


def _spoiled(signature: str) -> str:
    first = signature[:1]
    replacement = next(character for character in REPLACEMENT_CHARACTERS if character != first)
    return replacement + signature[1:]


def _decoded(part: str) -> bytes:
    return base64.urlsafe_b64decode(part + "=" * (-len(part) % 4))


def _encoded(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).rstrip(b"=").decode()
