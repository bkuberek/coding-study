"""Find the repeated tool calls of a failed agent run, and where its failure started.

The spans are fake, shaped like OpenTelemetry spans with the generative AI attributes, and listed
in the order they started; their times are left out. A tool call's arguments arrive as JSON text,
written a little differently from one call to the next.
"""

import json
from collections import Counter, defaultdict

LOOKUP = "execute_tool lookup_order"
GET = "GET /orders/{id}"


def agent(name: str) -> dict[str, str]:
    return {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": name}


def tool(name: str, arguments: str, error_type: str = "") -> dict[str, str]:
    attributes = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name,
                  "gen_ai.tool.call.arguments": arguments}
    return attributes | ({"error.type": error_type} if error_type else {})


CHAT = {"gen_ai.operation.name": "chat"}
TIMEOUT = {"error.type": "timeout"}
SPANS = [  # (span id, parent id, name, status, status description, attributes)
    ("r1", None, "invoke_agent support_bot", "error", "gave up: could not look up the order",
     agent("support_bot")),
    ("m1", "r1", "chat small-model", "unset", "", CHAT),
    ("c1", "r1", "execute_tool get_customer", "unset", "",
     tool("get_customer", '{"email": "kim@example.com"}')),
    ("h1", "r1", "invoke_agent docs_helper", "unset", "", agent("docs_helper")),
    ("d1", "h1", "execute_tool search_docs", "error", "the index refused: too many requests",
     tool("search_docs", '{"query": "refund policy"}', "rate_limited")),
    ("d2", "h1", "execute_tool search_docs", "unset", "",
     tool("search_docs", '{"query":"refund policy"}')),
    ("m2", "r1", "chat small-model", "unset", "", CHAT),
    ("c2", "r1", "execute_tool get_customer", "unset", "",
     tool("get_customer", '{"email":"kim@example.com"}')),
    ("t1", "r1", LOOKUP, "error", "the order service did not answer",
     tool("lookup_order", '{"order_id": "A17", "fields": ["status"]}', "timeout")),
    ("g1", "t1", GET, "error", "no answer after 2 s", TIMEOUT),
    ("m3", "r1", "chat small-model", "unset", "", CHAT),
    ("t2", "r1", LOOKUP, "error", "the order service did not answer",
     tool("lookup_order", '{"fields": ["status"], "order_id": "A17"}', "timeout")),
    ("g2", "t2", GET, "error", "no answer after 2 s", TIMEOUT),
    ("m4", "r1", "chat small-model", "unset", "", CHAT),
    ("t3", "r1", LOOKUP, "error", "the order service did not answer",
     tool("lookup_order", '{ "order_id" : "A17", "fields" : [ "status" ] }', "timeout")),
    ("g3", "t3", GET, "error", "no answer after 2 s", TIMEOUT),
    ("m5", "r1", "chat small-model", "unset", "", CHAT),
]

spans = {}
children = defaultdict(list)
for span_id, parent_id, name, status, description, attributes in SPANS:
    spans[span_id] = {"parent": parent_id, "name": name, "status": status,
                      "description": description, "attributes": attributes}
    if parent_id is not None:
        children[parent_id].append(span_id)
root = next(span_id for span_id, span in spans.items() if span["parent"] is None)


def fingerprint(attributes: dict[str, str]) -> str:
    """The tool and its arguments in one canonical form: parsed, keys sorted, no spaces."""
    arguments = json.loads(attributes["gen_ai.tool.call.arguments"])
    canonical = json.dumps(arguments, sort_keys=True, separators=(",", ":"))
    return f"{attributes['gen_ai.tool.name']} {canonical}"


def calling_agent(span_id: str) -> str:
    """The name of the nearest enclosing agent span."""
    parent = spans[span_id]["parent"]
    while spans[parent]["attributes"].get("gen_ai.operation.name") != "invoke_agent":
        parent = spans[parent]["parent"]
    return spans[parent]["attributes"]["gen_ai.agent.name"]


calls = defaultdict(list)  # (agent, fingerprint) -> statuses, in the order the calls started
for span_id, span in spans.items():
    if span["attributes"].get("gen_ai.operation.name") == "execute_tool":
        calls[(calling_agent(span_id), fingerprint(span["attributes"]))].append(span["status"])

print("repeated tool calls:")
for (agent_name, call), statuses in calls.items():
    if len(statuses) < 2:
        continue
    failed = statuses.count("error")
    if failed == len(statuses):
        verdict = "a retry loop, every call failed"
    elif failed:
        verdict = "retried until it worked"
    else:
        verdict = "the same result fetched again"
    print(f"  {agent_name} called {call}")
    print(f"    {len(statuses)} calls, {failed} failed: {verdict}")

origins = Counter()


def follow_failures(span_id: str, path: list[str]) -> None:
    """Walk down along failed children, to the failed spans that have no failed child."""
    failed = [child for child in children[span_id] if spans[child]["status"] == "error"]
    if not failed:
        span = spans[span_id]
        cause = f"error.type {span['attributes'].get('error.type')}: {span['description']}"
        origins[(" > ".join(spans[step]["name"] for step in path), cause)] += 1
    for child in failed:
        follow_failures(child, [*path, child])


print(f"the run failed: {spans[root]['name']}: {spans[root]['description']}")
follow_failures(root, [root])
print("where it started, following the failed children down from the root:")
for (path, cause), count in origins.items():
    print(f"  {count} times: {path}")
    print(f"    {cause}")
print("failures that were handled, under a parent that did not fail:")
for span in spans.values():
    parent = spans.get(span["parent"])
    if span["status"] == "error" and parent and parent["status"] != "error":
        print(f"  {span['name']} under {parent['name']}: {span['description']}")
