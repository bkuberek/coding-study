"""The order in which a pipeline's tasks can run, with the standard library's graphlib.

Each task maps to the tasks it depends on. TopologicalSorter hands out, in rounds, every task whose
inputs are all done; the tasks of one round could run in parallel. A cycle has no valid order.
"""

from graphlib import CycleError, TopologicalSorter

PIPELINE = {  # task -> the tasks it depends on
    "load_orders": [],
    "load_rates": [],
    "clean_orders": ["load_orders"],
    "daily_revenue": ["clean_orders", "load_rates"],
    "churn_report": ["clean_orders"],
    "weekly_revenue": ["daily_revenue"],
}


def rounds(graph: dict[str, list[str]]) -> list[list[str]]:
    sorter = TopologicalSorter(graph)
    sorter.prepare()  # raises CycleError if the graph has a cycle
    result = []
    while sorter.is_active():
        ready = sorted(sorter.get_ready())  # sorted, so the output does not depend on insertion
        result.append(ready)
        sorter.done(*ready)
    return result


for number, tasks in enumerate(rounds(PIPELINE), start=1):
    print(f"round {number}: {', '.join(tasks)}")

broken = {**PIPELINE, "load_rates": ["weekly_revenue"]}  # rates now read the weekly report
try:
    rounds(broken)
except CycleError as error:
    print("cycle:", " -> ".join(error.args[1]))
