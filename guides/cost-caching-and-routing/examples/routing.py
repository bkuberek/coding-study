"""What a batch of requests costs on one large model, on a cascade from a small one, and with output limits.

Prices are invented, in credits per million tokens. The models' answers are recorded data.
"""

PRICES = {"small": (0.2, 0.8), "large": (3.0, 15.0)}  # (per million prompt tokens, per million completion tokens)

# (prompt tokens, completion tokens, does the small model's answer pass the validator?)
REQUESTS = [(900, 120, True), (1200, 200, True), (800, 90, True), (1500, 400, False), (1000, 150, True),
            (700, 60, True), (2000, 600, False), (950, 110, True), (1100, 180, True), (1300, 250, True)]


def cost(model: str, prompt: int, completion: int) -> float:
    per_prompt, per_completion = PRICES[model]
    return (prompt * per_prompt + completion * per_completion) / 1_000_000


large_only = sum(cost("large", p, c) for p, c, _ in REQUESTS)
cascade, escalated = 0.0, 0
for prompt, completion, passes in REQUESTS:
    cascade += cost("small", prompt, completion)  # always try the small model first
    if not passes:  # the validator rejects its answer: pay again for the large model
        cascade += cost("large", prompt, completion)
        escalated += 1
print(f"large model for everything: {large_only:.4f} credits")
print(f"cascade, {escalated} of {len(REQUESTS)} escalated: {cascade:.4f} credits ({cascade / large_only:.0%} of it)")

# If the router could tell the hard requests from the easy ones up front, nothing would be paid twice.
routed = sum(cost("small" if passes else "large", p, c) for p, c, passes in REQUESTS)
print(f"a perfect router: {routed:.4f} credits ({routed / large_only:.0%})")

# Output tokens cost five times as much as prompt tokens here; an output limit caps the worst case.
for limit in (None, 200):
    total = sum(cost("large", p, c if limit is None else min(c, limit)) for p, c, _ in REQUESTS)
    cut = 0 if limit is None else sum(c > limit for _, c, _ in REQUESTS)
    print(f"large model, output limit {limit}: {total:.4f} credits, {cut} answers cut short")
