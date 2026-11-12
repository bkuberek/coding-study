"""Three caches in front of a model: exact responses, a stable prompt prefix, and similar questions.

Tokens are counted as words. The embedding model is a fake that maps known words to named axes.
"""

import hashlib
import json
import math


# 1. An exact response cache: the key is a hash of the whole request in one canonical form.
def cache_key(request: dict) -> str:
    canonical = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


first = {"model": "small", "temperature": 0, "messages": [{"role": "user", "content": "Refund window?"}]}
same = {"messages": [{"content": "Refund window?", "role": "user"}], "temperature": 0, "model": "small"}
spaced = {"model": "small", "temperature": 0, "messages": [{"role": "user", "content": "Refund window? "}]}
print("same request, keys in another order:", cache_key(first) == cache_key(same))
print("one trailing space:", cache_key(first) == cache_key(spaced))


# 2. Prompt caching reuses the work done on an identical start of the prompt, so its order matters.
INSTRUCTIONS = "You answer questions about the shop's policies. " * 20
TOOLS = "Tools: search_kb(query), lookup_order(order_id). " * 10


def shared_prefix(a: str, b: str) -> int:
    count = 0
    for x, y in zip(a.split(), b.split()):
        if x != y:
            break
        count += 1
    return count


def stable(turn: str, time: str) -> str:
    return f"{INSTRUCTIONS}{TOOLS}Question: {turn} (asked at {time})"


def unstable(turn: str, time: str) -> str:
    return f"Now: {time}. {INSTRUCTIONS}{TOOLS}Question: {turn}"


for layout in (stable, unstable):
    a, b = layout("Refund window?", "09:00"), layout("Where is my order?", "09:01")
    print(f"{layout.__name__:>8} layout: {shared_prefix(a, b)} of {len(b.split())} tokens shared with the last request")

# 3. A semantic cache answers a new question with the answer to a similar earlier one.
AXES = ("refund", "replacement", "time", "shipping")
WORDS = {"refund": "refund", "money": "refund", "back": "refund", "replacement": "replacement",
         "exchange": "replacement", "long": "time", "days": "time", "when": "time", "ship": "shipping"}


def embed(text: str) -> list[float]:
    counts = [0.0] * len(AXES)
    for word in text.lower().replace("?", "").replace(",", "").split():
        if word in WORDS:
            counts[AXES.index(WORDS[word])] += 1
    length = math.sqrt(sum(c * c for c in counts))
    return [c / length for c in counts] if length else counts


cached = {"How long do I have to ask for a refund?": "30 days from purchase."}
for question in ["How many days do I have to get my money back?", "How long, in days, do I have to ask for a replacement?",
                 "When do you ship?"]:
    best, score = max(((q, sum(x * y for x, y in zip(embed(q), embed(question)))) for q in cached), key=lambda p: p[1])
    verdicts = [f"at {threshold}: {'hit' if score >= threshold else 'miss'}" for threshold in (0.6, 0.9)]
    print(f"{question!r} similarity {score:.2f}, {', '.join(verdicts)}")
print("a hit answers with:", repr(cached["How long do I have to ask for a refund?"]))
