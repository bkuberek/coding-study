"""A signed token: the signature shows who wrote it, and the claims say who and what it is for.

A toy format with a shared key (HMAC-SHA256), so that it runs on the standard library alone.
Real tokens use a standard format, such as a JSON Web Token, and a maintained library.
"""

import base64
import hashlib
import hmac
import json

ISSUER_KEY = b"key shared by the login service and its APIs"  # in practice, from a secret store


def encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign(claims: dict) -> str:
    body = encode(json.dumps(claims, sort_keys=True).encode())
    tag = hmac.new(ISSUER_KEY, body.encode(), hashlib.sha256).digest()
    return body + "." + encode(tag)


def verified_claims(token: str) -> dict | None:
    """The claims, if the signature matches; None if anyone but the key holder wrote them."""
    body, _, tag = token.partition(".")
    expected = hmac.new(ISSUER_KEY, body.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(decode(tag), expected):
        return None
    return json.loads(decode(body))


def accept(token: str, me: str) -> str:
    claims = verified_claims(token)
    if claims is None:
        return "refused: bad signature"
    if claims["aud"] != me:
        return f"refused: token is for {claims['aud']!r}, not {me!r}"
    return f"accepted: {claims['sub']} may use {me}"


token = sign({"sub": "ana", "aud": "reports-api", "role": "viewer"})
print(accept(token, "reports-api"))

body, _, tag = token.partition(".")
forged_body = encode(json.dumps({"aud": "reports-api", "role": "admin", "sub": "ana"},
                                sort_keys=True).encode())
print(accept(forged_body + "." + tag, "reports-api"))

print(accept(token, "payments-api"))
