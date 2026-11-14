"""Plan the changes from what exists to what is wanted, apply them, and plan again.

Each resource has an address, `type/name`, and attributes. Some attributes cannot change on a
resource that exists: changing one replaces the resource. The plan remembers a fingerprint of
the state it was computed from, and applying it refuses when that state has changed since.
"""

import copy
import hashlib
import json

IMMUTABLE = {"disk": {"zone"}, "server": {"zone"}}

desired = {
    "bucket/logs": {"region": "eu", "versioning": "on"},
    "disk/data": {"size_gb": "100", "zone": "eu-2"},
    "server/web": {"size": "large", "zone": "eu-1"},
}
actual = {
    "disk/data": {"size_gb": "100", "zone": "eu-1"},
    "server/old": {"size": "small", "zone": "eu-1"},
    "server/web": {"size": "small", "zone": "eu-1"},
}


def fingerprint(state: dict) -> str:
    text = json.dumps(state, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def plan(desired: dict, actual: dict) -> dict:
    steps = []
    for address in sorted(desired.keys() | actual.keys()):
        want, have = desired.get(address), actual.get(address)
        if have is None:
            steps.append(("create", address, sorted(want.items())))
            continue
        if want is None:
            steps.append(("delete", address, []))
            continue
        changes = [(key, have.get(key), want.get(key))
                   for key in sorted(want.keys() | have.keys()) if have.get(key) != want.get(key)]
        forced = {key for key, _, _ in changes} & IMMUTABLE.get(address.split("/")[0], set())
        action = "replace" if forced else "update" if changes else "no-op"
        steps.append((action, address, changes))
    return {"based_on": fingerprint(actual), "steps": steps}


def show(the_plan: dict) -> None:
    print(f"plan based on state {the_plan['based_on']}:")
    for action, address, details in the_plan["steps"]:
        print(f"  {action:8} {address}  {details if details else ''}".rstrip())


def apply(the_plan: dict, actual: dict) -> None:
    if fingerprint(actual) != the_plan["based_on"]:
        raise RuntimeError("the state changed since this plan was made: plan again")
    for action, address, _ in the_plan["steps"]:
        if action in ("create", "update", "replace"):
            actual[address] = copy.deepcopy(desired[address])  # a replace makes a new resource
        elif action == "delete":
            del actual[address]


first = plan(desired, actual)
show(first)
apply(first, actual)
show(plan(desired, actual))

desired["server/web"]["size"] = "xlarge"
second = plan(desired, actual)
show(second)
actual["server/web"]["size"] = "medium"  # someone changes the server by hand
try:
    apply(second, actual)
except RuntimeError as refusal:
    print("apply refused:", refusal)
