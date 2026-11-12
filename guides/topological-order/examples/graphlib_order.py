"""Python's standard library sorts a graph topologically: graphlib.TopologicalSorter, since 3.9.

It takes the same shape as `needs`: each node mapped to the nodes that must come before it."""

from graphlib import CycleError, TopologicalSorter

needs = {
    "db": ["config"],
    "cache": ["config"],
    "auth": ["db", "cache"],
    "web": ["auth"],
}
print("order:", list(TopologicalSorter(needs).static_order()))

needs["config"] = ["auth"]
try:
    list(TopologicalSorter(needs).static_order())
except CycleError as error:
    print("CycleError, one cycle:", error.args[1])
