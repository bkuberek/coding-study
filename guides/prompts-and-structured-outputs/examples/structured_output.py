"""Ask a model for JSON, then trust only what passes a strict parse and a schema check.

The model is a fake that plays back scripted replies, so the example needs no network.
"""

import json

CATEGORIES = ("billing", "bug", "account", "other")
SCHEMA_TEXT = (
    '{"category": one of "billing", "bug", "account", "other", '
    '"priority": an integer from 1 to 3, "summary": a string of at most 80 characters}'
)


class ScriptedModel:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.requests: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.requests.append(messages)
        return self.replies.pop(0)


def messages_for(ticket: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": f"Classify the support ticket. Reply with JSON only: {SCHEMA_TEXT}."},
        {"role": "user", "content": "<ticket>I was charged twice this month.</ticket>"},
        {"role": "assistant", "content": '{"category": "billing", "priority": 2, "summary": "Charged twice"}'},
        {"role": "user", "content": f"<ticket>{ticket}</ticket>"},
    ]


def no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    keys = [key for key, _ in pairs]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise ValueError(f"repeated keys {repeated}")
    return dict(pairs)


def reject_constant(name: str) -> None:
    raise ValueError(f"{name} is not valid JSON")


def parse(reply: str) -> dict[str, object]:
    """Returns the ticket fields, or raises ValueError saying what is wrong."""
    value = json.loads(reply, object_pairs_hook=no_duplicate_keys, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise ValueError("the reply is not a JSON object")
    if set(value) != {"category", "priority", "summary"}:
        raise ValueError(f"keys {sorted(value)} are not exactly category, priority, summary")
    if value["category"] not in CATEGORIES:
        raise ValueError(f"category {value['category']!r} is not one of {list(CATEGORIES)}")
    priority = value["priority"]
    if type(priority) is not int or not 1 <= priority <= 3:
        raise ValueError(f"priority {priority!r} is not an integer from 1 to 3")
    if not isinstance(value["summary"], str) or len(value["summary"]) > 80:
        raise ValueError("summary is not a string of at most 80 characters")
    return value


def classify(model: ScriptedModel, ticket: str, attempts: int = 2) -> tuple[dict[str, object] | None, list[str]]:
    """The fields and the problems found on the way, or None when every attempt failed."""
    messages, problems = messages_for(ticket), []
    for _ in range(attempts):
        reply = model.complete(messages)
        try:
            return parse(reply), problems
        except ValueError as problem:
            problems.append(str(problem))
            messages = [*messages, {"role": "assistant", "content": reply},
                        {"role": "user", "content": f"Invalid: {problem}. Reply with corrected JSON only."}]
    return None, problems


GOOD = '{"category": "bug", "priority": 1, "summary": "Export crashes"}'
scripts = {
    "plain JSON": [GOOD],
    "prose around it": ['Sure! Here is the JSON: ' + GOOD, GOOD],
    "invented category": ['{"category": "crash", "priority": 1, "summary": "Export crashes"}', GOOD],
    "repeated key": ['{"category": "bug", "priority": 3, "priority": 1, "summary": "Export crashes"}', GOOD],
    "NaN": ['{"category": "bug", "priority": NaN, "summary": "Export crashes"}', GOOD],
    "priority as text": ['{"category": "bug", "priority": "1", "summary": "Export crashes"}',
                         '{"category": "bug", "priority": "high", "summary": "Export crashes"}'],
}
for case, script in scripts.items():
    model = ScriptedModel(script)
    fields, problems = classify(model, "The export button crashes the app.")
    outcome = "rejected" if fields is None else f"accepted {fields['category']}/{fields['priority']}"
    print(f"{case}: {len(model.requests)} request(s), {outcome}")
    for problem in problems:
        print(f"    invalid: {problem}")

print("json.loads alone keeps the last repeated key:", json.loads(scripts["repeated key"][0])["priority"])
print("json.loads alone accepts NaN:", json.loads(scripts["NaN"][0])["priority"])
print("roles of the first request:", [message["role"] for message in messages_for("...")])
