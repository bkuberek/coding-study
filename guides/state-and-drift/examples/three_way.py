"""Compare what you want, what the tool recorded, and what a scan of the real world found.

The record and the scan are matched by the id the provider gave each resource, never by name.
For each attribute, the three values tell apart a change you made in the description (pending),
a change made outside the tool alone (drift), both at once (conflict), and a world that already
agrees with what you want while the record lags behind (stale record). The findings are printed
grouped by verdict.
"""

desired = {
    "vm/build": {"cpus": "8", "memory_gb": "32", "image": "builder-7"},
    "vm/docs": {"cpus": "2", "memory_gb": "4", "image": "web-3"},
    "volume/cache": {"tier": "fast"},
}
recorded = {  # address -> (provider id, attributes when the tool last touched it)
    "vm/build": ("vm-31", {"cpus": "4", "memory_gb": "16", "image": "builder-7"}),
    "vm/docs": ("vm-32", {"cpus": "2", "memory_gb": "4", "image": "web-2"}),
    "volume/cache": ("vol-b", {"tier": "fast"}),
}
scanned = {  # provider id -> (type, attributes now)
    "vm-31": ("vm", {"cpus": "8", "memory_gb": "24", "image": "builder-7"}),
    "vm-32": ("vm", {"cpus": "4", "memory_gb": "4", "image": "web-2"}),
    "b-12": ("bucket", {"region": "south"}),
}
ORDER = ["unmanaged", "deleted outside the tool", "conflict", "drift", "pending", "stale record"]


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


findings: dict[str, list[str]] = {verdict: [] for verdict in ORDER}
managed_ids = {resource_id for resource_id, _ in recorded.values()}
for resource_id in sorted(scanned.keys() - managed_ids):
    findings["unmanaged"].append(f"{resource_id} ({scanned[resource_id][0]}): no record names it")
for address in sorted(recorded):
    resource_id, record = recorded[address]
    if resource_id not in scanned:
        findings["deleted outside the tool"].append(f"{address} ({resource_id})")
        continue
    world, want = scanned[resource_id][1], desired.get(address, {})
    for key in sorted(want.keys() | record.keys() | world.keys()):
        values = want.get(key), record.get(key), world.get(key)
        verdict = classify(*values)
        if verdict != "in sync":
            findings[verdict].append(
                f"{address}.{key}: want={values[0]} record={values[1]} world={values[2]}")
for verdict in ORDER:
    for line in findings[verdict]:
        print(f"{verdict:24} {line}")
