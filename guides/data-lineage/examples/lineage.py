"""A lineage graph built from run events, walked upstream and downstream.

Each finished job run reports the datasets it read and wrote, as an OpenLineage run event trimmed
to the fields read here: a real one also carries its time, a run id, its producer and a schema URL.
Joining those reports gives a graph from every dataset to the datasets built from it. One output
also carries column-level lineage: which input columns each column comes from, and how.
"""


def run(job: str, inputs: list[str], outputs: list[str], columns: dict | None = None) -> dict:
    facets = {"columnLineage": {"fields": columns}} if columns else {}
    return {
        "eventType": "COMPLETE",
        "job": {"namespace": "shop", "name": job},
        "inputs": [{"namespace": "shop", "name": name} for name in inputs],
        "outputs": [{"namespace": "shop", "name": name, "facets": facets} for name in outputs],
    }


def field(name: str, column: str, kind: str, subtype: str) -> dict:
    return {"namespace": "shop", "name": name, "field": column,
            "transformations": [{"type": kind, "subtype": subtype, "masking": False}]}


EVENTS = [
    run("ingest_orders", [], ["raw.orders"]),
    run("ingest_rates", [], ["raw.fx_rates"]),
    run("ingest_customers", [], ["raw.customers"]),
    run("build_order_facts", ["raw.orders", "raw.fx_rates"], ["mart.order_facts"]),
    run("build_churn", ["mart.order_facts", "raw.customers"], ["mart.churn"]),
    run("build_revenue", ["mart.order_facts"], ["mart.daily_revenue"], {
        "total": {"inputFields": [
            field("mart.order_facts", "amount_eur", "DIRECT", "AGGREGATION"),
            field("mart.order_facts", "status", "INDIRECT", "FILTER")]},
        "day": {"inputFields": [field("mart.order_facts", "order_date", "DIRECT", "IDENTITY")]},
    }),
    run("export_finance", ["mart.daily_revenue"], ["export.finance_report"]),
]

readers: dict[str, set[str]] = {}  # dataset -> datasets built from it
sources: dict[str, set[str]] = {}  # dataset -> datasets it is built from
for event in EVENTS:
    for output in event["outputs"]:
        sources.setdefault(output["name"], set())
        for source in event["inputs"]:
            readers.setdefault(source["name"], set()).add(output["name"])
            sources[output["name"]].add(source["name"])


def walk(start: str, edges: dict[str, set[str]]) -> list[str]:
    seen: set[str] = set()
    stack = [start]
    while stack:
        for nxt in edges.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return sorted(seen)


print("upstream of export.finance_report:", walk("export.finance_report", sources))
print("downstream of raw.fx_rates:", walk("raw.fx_rates", readers))
revenue = next(e for e in EVENTS if e["job"]["name"] == "build_revenue")["outputs"][0]
for column, lineage in revenue["facets"]["columnLineage"]["fields"].items():
    for source in lineage["inputFields"]:
        how = source["transformations"][0]
        print(f"daily_revenue.{column} <- {source['name']}.{source['field']}"
              f" ({how['type']}, {how['subtype']})")
