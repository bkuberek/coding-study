EVERY = "*"
SEPARATOR = "/"


class PolicyEngine:
    def __init__(self) -> None:
        self._parents: dict[str, list[str]] = {}
        self._roles_of: dict[str, list[str]] = {}
        self._rules_of: dict[str, list[tuple[str, str, str]]] = {}

    def inherit(self, role: str, parent_role: str) -> None:
        self._parents.setdefault(role, []).append(parent_role)

    def assign_role(self, principal: str, role: str) -> None:
        self._roles_of.setdefault(principal, []).append(role)

    def add_rule(self, role: str, effect: str, action: str, resource: str) -> None:
        self._rules_of.setdefault(role, []).append((effect, action, resource))

    def check(self, principal: str, action: str, resource: str) -> str:
        covering = _covering_resources(resource)
        decision = "default-deny"
        for role in self._effective_roles(principal):
            for effect, rule_action, rule_resource in self._rules_of.get(role, ()):
                if rule_action in (action, EVERY) and rule_resource in covering:
                    if effect == "deny":
                        return "deny"
                    decision = "allow"
        return decision

    def _effective_roles(self, principal: str) -> set[str]:
        # One visited set for the whole walk: a cycle ends, and a diamond is walked once.
        seen: set[str] = set()
        pending = list(self._roles_of.get(principal, ()))
        while pending:
            role = pending.pop()
            if role not in seen:
                seen.add(role)
                pending.extend(self._parents.get(role, ()))
        return seen


def _covering_resources(resource: str) -> set[str]:
    covering = {EVERY, resource}
    while SEPARATOR in resource:
        resource = resource.rpartition(SEPARATOR)[0]
        covering.add(resource)
    return covering
