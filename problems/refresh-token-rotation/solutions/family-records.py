from dataclasses import dataclass


@dataclass
class _Family:
    current: str
    expires_at: int
    last_spent: str | None = None
    grace_ends_at: int = 0
    revoked: bool = False


class RefreshTokenStore:
    def __init__(self, ttl_seconds: int, grace_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._grace_seconds = grace_seconds
        self._families: dict[str, _Family] = {}
        # Every token ever issued, spent ones included: a spent token must still find its family.
        self._family_of_token: dict[str, _Family] = {}

    def issue(self, family_id: str, token_id: str, now: int) -> bool:
        if family_id in self._families or token_id in self._family_of_token:
            return False
        family = _Family(current=token_id, expires_at=now + self._ttl_seconds)
        self._families[family_id] = family
        self._family_of_token[token_id] = family
        return True

    def rotate(self, token_id: str, new_token_id: str, now: int) -> str:
        family = self._family_of_token.get(token_id)
        if family is None:
            return "unknown"
        if family.revoked:
            return "revoked"
        if token_id == family.current:
            if now >= family.expires_at:
                return "expired"
            self._replace_current(family, new_token_id, now)
            return "rotated"
        if token_id == family.last_spent and now < family.grace_ends_at:
            return "grace-retry"
        family.revoked = True
        return "reuse-detected"

    def active_token(self, family_id: str, now: int) -> str:
        family = self._families.get(family_id)
        if family is None or family.revoked or now >= family.expires_at:
            return ""
        return family.current

    def _replace_current(self, family: _Family, new_token_id: str, now: int) -> None:
        family.last_spent = family.current
        family.grace_ends_at = now + self._grace_seconds
        family.current = new_token_id
        family.expires_at = now + self._ttl_seconds
        self._family_of_token[new_token_id] = family
