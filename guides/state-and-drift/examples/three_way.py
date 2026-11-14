"""Compare what you want, what the tool recorded, and what a scan of the real world found.

The record and the scan are matched by the id the provider gave each resource, never by name.
For each attribute, the three values tell apart a change you made in the description (pending),
a change made outside the tool (drift), both at once (conflict), and a world that already
agrees with what you want while the record lags behind (stale record).
"""

desired = {
    "server/web": {"size": "large", "zone": "eu-1", "monitoring": "on"},
    "server/api": {"size": "small", "zone": "eu-2"},
    "disk/data": {"size_gb": "100"},
}
recorded = {  # address -> (provider id, attributes when the tool last touched it)
    "server/web": ("i-100", {"size": "medium", "zone": "eu-1", "monitoring": "off"}),
    "server/api": ("i-200", {"size": "small", "zone": "eu-1"}),
    "disk/data": ("vol-7", {"size_gb": "100"}),
}
scanned = {  # provider id -> (type, attributes now)
    "i-100": ("server", {"size": "large", "zone": "eu-1", "monitoring": "debug"}),
    "i-200": ("server", {"size": "xlarge", "zone": "eu-1"}),
    "i-999": ("bucket", {"region": "eu"}),
}


def classify(want: str | None, record: str | None, world: str | None) -> str:
    if want == record == world:
        return "in sync"
    if world == record:
        return "pending"
    if want == record:
        return "drift"
    if want == world:
        return "stale record"
    return "conflict"


managed_ids = set()
for address in sorted(recorded):
    resource_id, record = recorded[address]
    managed_ids.add(resource_id)
    if resource_id not in scanned:
        print(f"{address} ({resource_id}): deleted outside the tool")
        continue
    world = scanned[resource_id][1]
    want = desired.get(address, {})
    for key in sorted(want.keys() | record.keys() | world.keys()):
        values = want.get(key), record.get(key), world.get(key)
        verdict = classify(*values)
        if verdict != "in sync":
            print(f"{address}.{key}: want={values[0]} record={values[1]} world={values[2]}"
                  f" -> {verdict}")
for resource_id in sorted(scanned.keys() - managed_ids):
    print(f"{resource_id} ({scanned[resource_id][0]}): unmanaged, no record names it")
