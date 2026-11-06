import re

SINGLE_VALUED = ("iss", "exp", "nbf")
TIMESTAMPS = ("exp", "nbf")
REQUIRED = ("iss", "aud", "exp")
# fullmatch, and no \d or isdigit(): those accept digits of other scripts, and $ accepts a newline.
WHOLE_SECONDS = re.compile(r"[0-9]+")


def validate_claims(
    claims: list[list[str]],
    now: int,
    clock_skew_seconds: int,
    expected_issuer: str,
    expected_audience: str,
    required_scopes: list[str],
) -> str:
    values_of: dict[str, list[str]] = {}
    for name, *values in claims:
        if name in values_of:
            return "malformed-claim"
        values_of[name] = values
    if _is_malformed(values_of):
        return "malformed-claim"
    if any(name not in values_of for name in REQUIRED):
        return "missing-claim"
    if values_of["iss"][0] != expected_issuer:
        return "wrong-issuer"
    if expected_audience not in values_of["aud"]:
        return "wrong-audience"
    if now >= int(values_of["exp"][0]) + clock_skew_seconds:
        return "expired"
    if "nbf" in values_of and now + clock_skew_seconds < int(values_of["nbf"][0]):
        return "not-yet-valid"
    if not set(values_of.get("scope", ())).issuperset(required_scopes):
        return "insufficient-scope"
    return "ok"


def _is_malformed(values_of: dict[str, list[str]]) -> bool:
    if any(name in values_of and len(values_of[name]) != 1 for name in SINGLE_VALUED):
        return True
    if "aud" in values_of and not values_of["aud"]:
        return True
    return any(
        name in values_of and WHOLE_SECONDS.fullmatch(values_of[name][0]) is None
        for name in TIMESTAMPS
    )
