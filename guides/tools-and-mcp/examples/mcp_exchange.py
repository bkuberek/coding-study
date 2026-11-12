"""A tool call over the Model Context Protocol's message shapes, in one process: host, client and server.

The messages follow the 2026-07-28 revision: JSON-RPC 2.0, every request carrying its protocol version
and client capabilities in _meta, results tagged with resultType. The model and the user are scripted.
"""

import json

VERSION = "2026-07-28"
ORDERS = {"A-1001": "shipped", "A-1002": "processing"}
TOOLS = [
    {"name": "get_order", "description": "Read the status of one order.",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string", "pattern": "^A-[0-9]{4}$"}},
                     "required": ["order_id"], "additionalProperties": False},
     "annotations": {"readOnlyHint": True}},
    {"name": "cancel_order", "description": "Cancel an order that has not shipped.",
     "inputSchema": {"type": "object", "properties": {"order_id": {"type": "string", "pattern": "^A-[0-9]{4}$"}},
                     "required": ["order_id"], "additionalProperties": False}},
]


def schema_problem(schema: dict, arguments: dict) -> str:
    """Only the required keys; a real server checks the whole schema with a JSON Schema validator."""
    missing = [name for name in schema["required"] if name not in arguments]
    return f"missing {', '.join(missing)}" if missing else ""


def server(request: dict) -> dict:
    meta = request.get("params", {}).get("_meta", {})
    reply = {"jsonrpc": "2.0", "id": request["id"]}
    if "io.modelcontextprotocol/protocolVersion" not in meta or "io.modelcontextprotocol/clientCapabilities" not in meta:
        return reply | {"error": {"code": -32602, "message": "missing required _meta fields"}}
    if request["method"] == "tools/list":
        return reply | {"result": {"resultType": "complete", "tools": TOOLS}}
    name, arguments = request["params"]["name"], request["params"].get("arguments", {})
    tool = next((t for t in TOOLS if t["name"] == name), None)
    if tool is None:  # a protocol error: the request itself is wrong
        return reply | {"error": {"code": -32602, "message": f"Unknown tool: {name}"}}
    problem = schema_problem(tool["inputSchema"], arguments)  # tool execution errors: the model can fix these
    if not problem and arguments["order_id"] not in ORDERS:
        problem = f"no order {arguments['order_id']}"
    if not problem and name == "cancel_order" and ORDERS[arguments["order_id"]] == "shipped":
        problem = "a shipped order cannot be cancelled"
    if problem:
        return reply | {"result": {"resultType": "complete", "content": [{"type": "text", "text": problem}], "isError": True}}
    if name == "cancel_order":
        ORDERS[arguments["order_id"]] = "cancelled"
    text = f"{arguments['order_id']}: {ORDERS[arguments['order_id']]}"
    return reply | {"result": {"resultType": "complete", "content": [{"type": "text", "text": text}], "isError": False}}


class Client:
    """One client per server; every request is self-contained."""

    def __init__(self) -> None:
        self.next_id = 1

    def request(self, method: str, params: dict | None = None) -> dict:
        meta = {"io.modelcontextprotocol/protocolVersion": VERSION, "io.modelcontextprotocol/clientCapabilities": {}}
        message = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": {**(params or {}), "_meta": meta}}
        self.next_id += 1
        return server(message)


client = Client()
listing = client.request("tools/list")
print("tools offered to the model:", [tool["name"] for tool in listing["result"]["tools"]])

proposed = [  # what the scripted model asked for, in order
    ("get_order", {"order_id": "A-1002"}),
    ("get_order", {}),
    ("get_order", {"order_id": "A-9999"}),
    ("refund_order", {"order_id": "A-1002"}),
    ("cancel_order", {"order_id": "A-1001"}),
    ("cancel_order", {"order_id": "A-1002"}),
]
user_approves = {"A-1001": True, "A-1002": False}  # the person's answers to the confirmation prompts
for name, arguments in proposed:
    if name == "cancel_order" and not user_approves[arguments["order_id"]]:
        print(f"{name}{arguments}: the user declined, so the host never called the server")
        continue
    reply = client.request("tools/call", {"name": name, "arguments": arguments})
    if "error" in reply:
        print(f"{name}{arguments}: protocol error {reply['error']['code']}: {reply['error']['message']}")
    else:
        result = reply["result"]
        print(f"{name}{arguments}: isError={result['isError']}, {result['content'][0]['text']}")

print("a request without _meta:", server({"jsonrpc": "2.0", "id": 99, "method": "tools/list"})["error"])
print("the first request on the wire:")
print(" ", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": {
    "io.modelcontextprotocol/protocolVersion": VERSION, "io.modelcontextprotocol/clientCapabilities": {}}}}))
