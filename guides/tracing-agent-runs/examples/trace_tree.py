"""Rebuild the tree of an agent run from its spans, then roll tokens and cost up the tree.

The spans are fake, shaped like OpenTelemetry spans with the generative AI attributes, and listed
in the order an exporter would send them: each span once it ends, so children come before their
parents. Times are milliseconds from the start of the run.
"""

from collections import defaultdict

MODEL_CALLS = {"chat", "generate_content", "text_completion", "embeddings"}

# Price per million tokens, in whole units of some currency, so that tokens * price is an exact
# whole number of millionths of a unit. Made-up prices for made-up models.
PRICES = {
    "small-model": {"input": 2, "cached": 1, "output": 8},
    "large-model": {"input": 20, "cached": 5, "output": 80},
}

SPANS = [  # (span id, parent id, name, start, end, attributes)
    ("s2", "s1", "chat small-model", 100, 900, {
        "gen_ai.operation.name": "chat", "gen_ai.request.model": "small-model",
        "gen_ai.usage.input_tokens": 1200, "gen_ai.usage.output_tokens": 150}),
    ("s6", "s5", "chat small-model", 1100, 1500, {
        "gen_ai.operation.name": "chat", "gen_ai.request.model": "small-model",
        "gen_ai.usage.input_tokens": 300, "gen_ai.usage.output_tokens": 40}),
    ("s3", "s1", "execute_tool search_flights", 1000, 2200, {
        "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "search_flights"}),
    ("s7", "s5", "execute_tool fetch_rates", 1550, 2450, {
        "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "fetch_rates"}),
    ("s5", "s4", "invoke_agent currency_helper", 1050, 2550, {
        "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "currency_helper",
        "gen_ai.usage.input_tokens": 300, "gen_ai.usage.output_tokens": 40}),
    ("s4", "s1", "execute_tool convert_currency", 1000, 2600, {
        "gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": "convert_currency"}),
    ("s8", "s1", "chat large-model", 2700, 4900, {
        "gen_ai.operation.name": "chat", "gen_ai.request.model": "large-model",
        "gen_ai.usage.input_tokens": 4000, "gen_ai.usage.cache_read.input_tokens": 2500,
        "gen_ai.usage.output_tokens": 700}),
    ("s1", None, "invoke_agent trip_planner", 0, 5000, {
        "gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "trip_planner"}),
]

spans = {}
children = defaultdict(list)
roots = []
for span_id, parent_id, name, start, end, attributes in SPANS:
    spans[span_id] = {"name": name, "start": start, "end": end, "attributes": attributes}
    if parent_id is None:
        roots.append(span_id)
    else:
        children[parent_id].append(span_id)
for siblings in children.values():
    siblings.sort(key=lambda span_id: spans[span_id]["start"])


def own_usage(span_id: str) -> tuple[int, int, int]:
    """Input tokens, output tokens and cost in millionths of a unit, for a model call only."""
    attributes = spans[span_id]["attributes"]
    if attributes["gen_ai.operation.name"] not in MODEL_CALLS:
        return 0, 0, 0  # an agent's own token counts may repeat its model calls' counts
    model = attributes.get("gen_ai.response.model", attributes["gen_ai.request.model"])
    price = PRICES[model]
    inputs = attributes.get("gen_ai.usage.input_tokens", 0)
    cached = attributes.get("gen_ai.usage.cache_read.input_tokens", 0)  # already counted in inputs
    outputs = attributes.get("gen_ai.usage.output_tokens", 0)
    cost = (inputs - cached) * price["input"] + cached * price["cached"] + outputs * price["output"]
    return inputs, outputs, cost


subtree = {}


def roll_up(span_id: str) -> tuple[int, int, int]:
    """The span's own usage plus everything below it, computed children first."""
    total = list(own_usage(span_id))
    for child in children[span_id]:
        for i, value in enumerate(roll_up(child)):
            total[i] += value
    subtree[span_id] = tuple(total)
    return subtree[span_id]


def show(span_id: str, depth: int) -> None:
    span = spans[span_id]
    label = "  " * depth + span["name"]
    ms = span["end"] - span["start"]
    cost = own_usage(span_id)[2]
    inputs, outputs, total_cost = subtree[span_id]
    print(f"{label:<34}{ms:>6}{cost:>8}{total_cost:>9}{inputs:>8}/{outputs}")
    for child in children[span_id]:
        show(child, depth + 1)


print(f"{len(spans)} spans, {len(roots)} root; cost in millionths of a unit")
print(f"{'span':<34}{'ms':>6}{'own':>8}{'subtree':>9}  tokens in/out")
for root in roots:
    roll_up(root)
    show(root, 0)
agent = spans["s5"]["attributes"]
print("currency_helper's own counts:", agent["gen_ai.usage.input_tokens"], "in,",
      agent["gen_ai.usage.output_tokens"], "out, the same tokens as its model call, not added")
