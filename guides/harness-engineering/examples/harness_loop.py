"""The loop around an agent: budgets, a repeated-action guard, compaction and a completion check.

The model is a fake that plays back scripted steps; the tools and the test run are fakes too.
Tokens are counted as words.
"""

import hashlib
import json

WINDOW = 50  # tokens of context the model can take
COMPACT_AT = 0.7  # compact when the context passes this share of the window
KEEP_RECENT = 2  # entries kept word for word when compacting


def tokens(text: str) -> int:
    return len(text.split())


class FakeRepo:
    def __init__(self) -> None:
        self.edits = 0

    def run_tool(self, tool: str, argument: str) -> str:
        if tool == "read_file" and argument.startswith("tests/"):
            return "assert total([Item(price=2, quantity=3)]) == 6"
        if tool == "read_file":
            return "def total(items): return sum(item.price for item in items)  # quantity is ignored"
        if tool == "edit_file":
            self.edits += 1
            return f"edited {argument}"
        return self.tests()

    def tests(self) -> str:
        return "2 passed" if self.edits >= 2 else "1 failed: test_total_counts_quantity"


def run(steps: list[dict[str, str]], max_steps: int = 8, max_tokens: int = 400) -> None:
    repo, context, spent, seen = FakeRepo(), ["task: make test_total_counts_quantity pass"], 0, {}
    for number, step in enumerate(steps, start=1):
        if number > max_steps:
            print("  stop: the step limit was reached")
            return
        spent += sum(map(tokens, context))  # the model reads the whole context on every step
        if spent > max_tokens:
            print(f"  stop: the token budget was spent ({spent} > {max_tokens})")
            return
        if "done" in step:
            result = repo.tests()  # the harness checks the claim instead of believing it
            print(f"  step {number}: model says done -> check: {result}")
            if result.endswith("passed"):
                print(f"  finished after {number} steps, {spent} tokens read")
                return
            context.append(f"check failed: {result}")
            continue
        key = hashlib.sha256(json.dumps(step, sort_keys=True).encode()).hexdigest()
        seen[key] = seen.get(key, 0) + 1
        if seen[key] == 3:
            print(f"  stop: {step['tool']}({step['arg']}) proposed 3 times with the same arguments")
            return
        observation = repo.run_tool(step["tool"], step["arg"])
        context.append(f"{step['tool']}({step['arg']}) -> {observation}")
        print(f"  step {number}: {step['tool']}({step['arg']}) -> {observation}")
        if sum(map(tokens, context)) > COMPACT_AT * WINDOW:
            folded = len(context) - KEEP_RECENT
            summary = f"summary of {folded} earlier entries: total() ignores quantity; one test fails"
            context = [summary, *context[-KEEP_RECENT:]]  # a model call writes this summary
            print(f"    compacted: {folded} entries -> 1 summary, context now {sum(map(tokens, context))} tokens")


print("a run that finishes:")
run([
    {"tool": "read_file", "arg": "src/cart.py"},
    {"tool": "run_tests", "arg": "pytest -q"},
    {"tool": "edit_file", "arg": "src/cart.py"},
    {"done": "fixed"},
    {"tool": "edit_file", "arg": "src/cart.py"},
    {"done": "fixed"},
])
print("a run that repeats itself:")
run([{"tool": "run_tests", "arg": "pytest -q"}] * 5)
print("a run with a small token budget:")
run([{"tool": "read_file", "arg": "src/cart.py"}, {"tool": "read_file", "arg": "tests/test_cart.py"},
     {"tool": "run_tests", "arg": "pytest -q"}], max_tokens=40)
