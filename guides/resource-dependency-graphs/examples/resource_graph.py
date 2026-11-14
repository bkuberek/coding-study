"""Find the dependencies of resources from their references, and order creates and deletes.

A value `Ref(address, key)` stands for an attribute of another resource, known only once that
resource exists. Each reference is an edge of the dependency graph: the referring resource
needs the other one first. graphlib hands out the resources whose dependencies are all done,
one wave at a time; the waves are sorted so that the output is the same on every run.
"""

from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter


@dataclass(frozen=True)
class Ref:
    address: str
    key: str


resources = {
    "network/main": {"cidr": "10.0.0.0/16"},
    "subnet/a": {"network_id": Ref("network/main", "id"), "cidr": "10.0.1.0/24"},
    "subnet/b": {"network_id": Ref("network/main", "id"), "cidr": "10.0.2.0/24"},
    "firewall/web": {"network_id": Ref("network/main", "id"), "ports": "443"},
    "server/web": {"subnet_id": Ref("subnet/a", "id"), "firewall_id": Ref("firewall/web", "id")},
    "dns/www": {"target": Ref("server/web", "ip")},
    "bucket/logs": {"region": "eu"},
}


def dependencies(resources: dict) -> dict[str, set[str]]:
    return {address: {value.address for value in attributes.values() if isinstance(value, Ref)}
            for address, attributes in resources.items()}


def waves(needs: dict[str, set[str]]) -> list[list[str]]:
    sorter = TopologicalSorter(needs)
    sorter.prepare()  # raises CycleError if the graph has a cycle
    result = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())
        result.append(ready)
        sorter.done(*ready)
    return result


create = waves(dependencies(resources))
for number, wave in enumerate(create, 1):
    print(f"create wave {number}: {wave}")
deletes = [address for wave in reversed(create) for address in sorted(wave, reverse=True)]
print("delete order:", deletes)

resources["network/main"]["gateway"] = Ref("subnet/b", "gateway_ip")  # this closes a loop
try:
    waves(dependencies(resources))
except CycleError as error:
    print("cycle through:", sorted(set(error.args[1])))
