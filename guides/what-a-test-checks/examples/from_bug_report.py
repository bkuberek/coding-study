"""From a bug report to a regression test: reproduce, probe the boundaries, fix.

The report: "a 90-minute meeting shows as 1 h 30 min, but a meeting of exactly one hour shows as
60 min". The cases below are the values on each side of every boundary in the rule, with the
answer a person expects for each, written down before looking at what the code returns.
"""


def format_minutes_buggy(minutes: int) -> str:
    if minutes > 60:
        hours, rest = divmod(minutes, 60)
        return f"{hours} h" if rest == 0 else f"{hours} h {rest} min"
    return f"{minutes} min"


def format_minutes_fixed(minutes: int) -> str:
    if minutes >= 60:
        hours, rest = divmod(minutes, 60)
        return f"{hours} h" if rest == 0 else f"{hours} h {rest} min"
    return f"{minutes} min"


EXPECTED = {
    0: "0 min",
    1: "1 min",
    59: "59 min",
    60: "1 h",  # the case from the report
    61: "1 h 1 min",
    90: "1 h 30 min",  # the case the report says works
    119: "1 h 59 min",
    120: "2 h",
    121: "2 h 1 min",
}

print(f"{'minutes':>7}  {'expected':<11} {'buggy':<16} fixed")
for minutes, expected in EXPECTED.items():
    buggy = format_minutes_buggy(minutes)
    fixed = format_minutes_fixed(minutes)
    mark = "  FAIL" if buggy != expected else ""
    print(f"{minutes:>7}  {expected:<11} {buggy + mark:<16} {fixed}")
    assert fixed == expected, minutes
print("the fixed version passes every case")
