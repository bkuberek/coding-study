"""Two rules that disagree, and three ways a policy engine can combine them.

Each rule looks at attributes of the user, the document and the action (attribute-based access
control), and either applies to a request or does not. The combining algorithm decides what
happens when more than one applies, or none does.
"""

RULES = {
    "team-read": ("allow", lambda r: r["action"] == "read" and r["doc_team"] == r["user_team"]),
    "restricted": ("deny", lambda r: r["doc_label"] == "restricted" and not r["user_cleared"]),
}


def first_applicable(order: list[str], request: dict) -> str:
    for name in order:
        effect, applies = RULES[name]
        if applies(request):
            return effect
    return "no rule applies"


def deny_overrides(order: list[str], request: dict) -> str:
    effects = {RULES[name][0] for name in order if RULES[name][1](request)}
    if "deny" in effects:
        return "deny"
    return "allow" if "allow" in effects else "no rule applies"


def permit_overrides(order: list[str], request: dict) -> str:
    effects = {RULES[name][0] for name in order if RULES[name][1](request)}
    if "allow" in effects:
        return "allow"
    return "deny" if "deny" in effects else "no rule applies"


requests = {
    "own team, restricted": {"action": "read", "user_team": "audit", "doc_team": "audit",
                             "doc_label": "restricted", "user_cleared": False},
    "other team, public": {"action": "read", "user_team": "audit", "doc_team": "sales",
                           "doc_label": "public", "user_cleared": False},
}
orders = [["team-read", "restricted"], ["restricted", "team-read"]]

for label, request in requests.items():
    print(label)
    for combine in (first_applicable, deny_overrides, permit_overrides):
        answers = [combine(order, request) for order in orders]
        print(f"  {combine.__name__:17} {answers[0]:16} reversed: {answers[1]}")
