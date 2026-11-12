"""Two ways to keep a long conversation inside a budget: a context buffer and a rolling summary.

Tokens are counted as words. The summarizer is a fake that plays back scripted summaries.
"""

TURNS = [
    "user: hi, I'm Ana and I'm allergic to peanuts",
    "assistant: nice to meet you Ana, how can I help",
    "user: plan a dinner for four on Friday",
    "assistant: here is a menu with a satay starter, a curry and a mango dessert",
    "user: make the starter vegetarian",
    "assistant: the starter is now grilled vegetable skewers with satay sauce",
    "user: what should I buy first",
    "assistant: start with the vegetables and the satay sauce",
]
SCRIPTED_SUMMARIES = [
    "Ana is allergic to peanuts. She is planning a dinner for four on Friday.",
    "Ana is allergic to peanuts. Dinner for four on Friday: a satay starter, a curry, a mango dessert.",
    "Ana is allergic to peanuts. Dinner for four on Friday; the starter is now vegetarian.",
]
BUDGET = 45


def tokens(text: str) -> int:
    return len(text.split())


def buffer_view(turns: list[str], budget: int) -> list[str]:
    """The most recent turns that fit, newest kept first; older ones are simply dropped."""
    kept: list[str] = []
    for turn in reversed(turns):
        if tokens(turn) + sum(map(tokens, kept)) > budget:
            break
        kept.insert(0, turn)
    return kept


def summary_view(turns: list[str], budget: int, keep_recent: int = 2) -> list[str]:
    """Fold everything but the last turns into a summary whenever the context would overflow."""
    summaries = iter(SCRIPTED_SUMMARIES)
    summary, recent = "", []
    for turn in turns:
        recent.append(turn)
        context = ([f"summary: {summary}"] if summary else []) + recent
        if sum(map(tokens, context)) > budget:
            summary = next(summaries)  # a model call: old summary + folded turns -> new summary
            recent = recent[-keep_recent:]
    return ([f"summary: {summary}"] if summary else []) + recent


for name, view in (("buffer", buffer_view(TURNS, BUDGET)), ("rolling summary", summary_view(TURNS, BUDGET))):
    print(f"{name}: {sum(map(tokens, view))} tokens")
    for line in view:
        print("   ", line)
    print("    knows about the allergy:", any("peanut" in line for line in view))
