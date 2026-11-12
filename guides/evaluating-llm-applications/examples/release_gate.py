"""Score two versions of an assistant on a golden set with assertions and a pairwise judge, then gate.

The answers of both versions and the judge's verdicts are recorded data, so the example is fixed.
"""

import json
import math

GOLDEN = [  # (case id, must pass for release, checks on the answer)
    ("refund-window", True, [("contains", "30 days")]),
    ("refund-method", False, [("contains", "original payment method")]),
    ("leave-allowance", True, [("contains", "25 days")]),
    ("no-answer", True, [("contains", "don't know"), ("excludes", "password")]),
    ("json-ticket", True, [("json_field", "category")]),
    ("expenses-deadline", False, [("contains", "60 days")]),
    ("tone", False, [("excludes", "obviously")]),
    ("carry-over", False, [("contains", "5")]),
]
ANSWERS = {
    "baseline": {
        "refund-window": "Within 30 days of purchase.", "refund-method": "To the card you used.",
        "leave-allowance": "25 days a year.", "no-answer": "I don't know.",
        "json-ticket": '{"category": "billing"}', "expenses-deadline": "Within 60 days of the trip.",
        "tone": "Obviously, within 60 days.", "carry-over": "Up to 5 days.",
    },
    "candidate": {
        "refund-window": "You have 30 days from purchase.",
        "refund-method": "It goes back to the original payment method.",
        "leave-allowance": "25 days of paid leave a year.", "no-answer": "I don't know.",
        "json-ticket": '{"category": "billing"}', "expenses-deadline": "Submit within 60 days.",
        "tone": "Within 60 days of the trip.", "carry-over": "Unused days carry over.",
    },
}
# The judge saw both answers to two open questions twice, in both orders, and named the better position.
JUDGE = {"refund-method": ("second", "first"), "carry-over": ("first", "first")}


def check(answer: str, kind: str, value: str) -> bool:
    if kind == "contains":
        return value.lower() in answer.lower()
    if kind == "excludes":
        return value.lower() not in answer.lower()
    try:
        return value in json.loads(answer)
    except ValueError:
        return False


def passes(version: str) -> dict[str, bool]:
    return {case: all(check(ANSWERS[version][case], *c) for c in checks) for case, _, checks in GOLDEN}


def judged(case: str) -> str:
    """Baseline shown first, then candidate first: a win must survive the swap."""
    baseline_first, candidate_first = JUDGE[case]
    if baseline_first == "second" and candidate_first == "first":
        return "candidate"
    if baseline_first == "first" and candidate_first == "second":
        return "baseline"
    return "tie (the verdict followed the position)"


results = {version: passes(version) for version in ANSWERS}
print(f"{'case':>17} {'':8}  {'  '.join(ANSWERS)}")
for case, critical, _ in GOLDEN:
    marks = "  ".join(f"{'pass' if results[v][case] else 'FAIL':<{len(v)}}" for v in ANSWERS)
    print(f"{case:>17} {'critical' if critical else '        '}  {marks}".rstrip())
for case in JUDGE:
    print(f"judge on {case}: {judged(case)}")

n = len(GOLDEN)
for version in ANSWERS:
    rate = sum(results[version].values()) / n
    error = math.sqrt(rate * (1 - rate) / n)
    print(f"{version}: {rate:.0%} pass, give or take {error:.0%} (one standard error over {n} cases)")

broken = [case for case, critical, _ in GOLDEN if critical and not results["candidate"][case]]
regressed = [case for case, _, _ in GOLDEN if results["baseline"][case] and not results["candidate"][case]]
print("critical failures:", broken, "| regressions:", regressed)
print("gate:", "blocked" if broken or regressed else "passed")
