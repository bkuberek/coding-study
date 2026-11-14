"""A golden-file test: compare today's output with an approved copy, and show the difference.

The report includes the time it was made and a run id, which change on every run. They are
replaced by placeholders before the comparison, or the test would fail every time. When the
output really changes, the test fails with a line-by-line diff for a person to review.
"""

import difflib
import re

GOLDEN = """\
Invoice summary  generated <TIME>  run <RUN>
customer   items   total
cust-a         3   42.50
cust-b         1    9.99
total              52.49
"""


def render(rows: list[tuple[str, int, float]], generated: str, run_id: str) -> str:
    lines = [f"Invoice summary  generated {generated}  run {run_id}", "customer   items   total"]
    lines += [f"{name:<10} {items:>5} {total:>7.2f}" for name, items, total in rows]
    lines.append(f"{'total':<10} {'':>5} {sum(row[2] for row in rows):>7.2f}")
    return "\n".join(lines) + "\n"


def normalize(text: str) -> str:
    text = re.sub(r"generated \S+", "generated <TIME>", text)
    return re.sub(r"run [0-9a-f]{8}", "run <RUN>", text)


def check(output: str) -> list[str]:
    return list(difflib.unified_diff(GOLDEN.splitlines(), normalize(output).splitlines(),
                                     "golden", "actual", lineterm=""))


rows = [("cust-a", 3, 42.5), ("cust-b", 1, 9.99)]
today = render(rows, "2026-11-13T09:30:00Z", "3f9a0c1e")
print("same output, new time and run id:", "pass" if not check(today) else "fail")

rows_after_change = [("cust-a", 3, 42.5), ("cust-b", 1, 9.99), ("cust-c", 2, 0.0)]
diff = check(render(rows_after_change, "2026-11-14T08:00:00Z", "77b2e5d0"))
print("after a change:", "pass" if not diff else "fail")
print("\n".join(diff))
