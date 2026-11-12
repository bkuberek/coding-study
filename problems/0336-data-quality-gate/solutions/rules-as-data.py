import math
from bisect import bisect_right

ROW_CHECKS = frozenset({"not-null", "type", "allowed", "range", "unique", "references"})
BATCH_CHECKS = frozenset({"row-count", "drift", "freshness"})
ACTIONS = frozenset({"warn", "quarantine", "block"})
EMPTY_SHARE = 0.0001
DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


def is_int(text: str) -> bool:
    digits = text[1:] if text.startswith("-") else text
    return 1 <= len(digits) <= 15 and all("0" <= ch <= "9" for ch in digits)


def is_date(text: str) -> bool:
    if len(text) != 10 or text[4] != "-" or text[7] != "-":
        return False
    parts = (text[0:4], text[5:7], text[8:10])
    if not all(all("0" <= ch <= "9" for ch in part) for part in parts):
        return False
    year, month, day = (int(part) for part in parts)
    if year < 1 or not 1 <= month <= 12:
        return False
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    last = 29 if month == 2 and leap else DAYS_IN_MONTH[month - 1]
    return 1 <= day <= last


def ten_thousandths(decimal: str) -> int:
    """A non-negative decimal with at most four places, in units of 0.0001."""
    whole, _, fraction = decimal.partition(".")
    return int(whole) * 10000 + int((fraction + "0000")[:4])


class _Rule:
    __slots__ = ("rule_id", "check", "columns", "params", "action")

    def __init__(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> None:
        self.rule_id = rule_id
        self.check = check
        self.columns = columns
        self.params = params
        self.action = "block"


class QualityGate:
    """Rules are data: each one is a check name, its columns and its parameters, kept in the order
    they were added. Validation runs every rule over the rows and reports what failed; the gate
    runs the row rules first, sets aside the rows that quarantine rules reject, and runs the batch
    rules on what is left."""

    def __init__(self, columns: list[str]) -> None:
        self._index = {name: at for at, name in enumerate(columns)}
        self._rules: list[_Rule] = []
        self._by_id: dict[str, _Rule] = {}
        self._dimensions: dict[str, set[str]] = {}
        self._previous: list[list[str]] | None = None
        self._now = 0
        self._quarantined: list[int] = []

    # Level 1
    def add_rule(self, rule_id: str, check: str, columns: list[str], params: list[str]) -> bool:
        known = check in ROW_CHECKS or check in BATCH_CHECKS
        if rule_id in self._by_id or not known or any(c not in self._index for c in columns):
            return False
        if check == "references" and params[0] not in self._dimensions:
            return False
        rule = _Rule(rule_id, check, list(columns), list(params))
        self._rules.append(rule)
        self._by_id[rule_id] = rule
        return True

    def validate(self, rows: list[list[str]]) -> list[list[str]]:
        return [entry for rule in self._rules for entry in self._findings(rule, rows)]

    def failing_rows(self, rows: list[list[str]], rule_id: str) -> list[int]:
        rule = self._by_id.get(rule_id)
        if rule is None or rule.check in BATCH_CHECKS:
            return []
        failing = set()
        for column, bad in self._row_failures(rule, rows).items():
            failing.update(bad)
        return sorted(failing)

    # Level 2
    def load_dimension(self, name: str, keys: list[str]) -> int:
        self._dimensions[name] = set(keys)
        return len(self._dimensions[name])

    def set_previous_batch(self, rows: list[list[str]]) -> int:
        self._previous = [list(row) for row in rows]
        return len(rows)

    # Level 3
    def set_time(self, now: int) -> None:
        self._now = now

    # Level 4
    def set_action(self, rule_id: str, action: str) -> bool:
        rule = self._by_id.get(rule_id)
        if rule is None or action not in ACTIONS:
            return False
        if action == "quarantine" and rule.check in BATCH_CHECKS:
            return False
        rule.action = action
        return True

    def decide(self, rows: list[list[str]]) -> list[list[str]]:
        findings: list[list[str]] = []
        set_aside: set[int] = set()
        for rule in self._rules:
            if rule.check in ROW_CHECKS:
                entries = self._findings(rule, rows)
                findings.extend([*entry, rule.action] for entry in entries)
                if rule.action == "quarantine":
                    set_aside.update(self.failing_rows(rows, rule.rule_id))
        kept = [row for at, row in enumerate(rows) if at not in set_aside]
        for rule in self._rules:
            if rule.check in BATCH_CHECKS:
                findings.extend([*entry, rule.action] for entry in self._findings(rule, kept))
        order = {rule.rule_id: rank for rank, rule in enumerate(self._rules)}
        findings.sort(key=lambda entry: order[entry[0]])
        if any(entry[3] == "block" for entry in findings):
            self._quarantined = []
            return [["block", "0", "0"], *findings]
        self._quarantined = sorted(set_aside)
        self._previous = kept
        return [["publish", str(len(kept)), str(len(set_aside))], *findings]

    def quarantined(self) -> list[int]:
        return list(self._quarantined)

    # Helpers
    def _findings(self, rule: _Rule, rows: list[list[str]]) -> list[list[str]]:
        if rule.check == "unique":
            bad = self._row_failures(rule, rows)["+".join(rule.columns)]
            return [[rule.rule_id, "+".join(rule.columns), str(len(bad))]] if bad else []
        if rule.check in ROW_CHECKS:
            return [
                [rule.rule_id, column, str(len(bad))]
                for column, bad in self._row_failures(rule, rows).items()
                if bad
            ]
        observed = self._batch_failure(rule, rows)
        return [] if observed is None else [[rule.rule_id, "".join(rule.columns), observed]]

    def _row_failures(self, rule: _Rule, rows: list[list[str]]) -> dict[str, list[int]]:
        """For each column of a row rule, the indexes of the rows that fail it."""
        if rule.check == "unique":
            seen: dict[tuple[str, ...], list[int]] = {}
            for at, row in enumerate(rows):
                key = tuple(row[self._index[c]] for c in rule.columns)
                if "" not in key:
                    seen.setdefault(key, []).append(at)
            bad = sorted(at for group in seen.values() if len(group) > 1 for at in group)
            return {"+".join(rule.columns): bad}
        failures: dict[str, list[int]] = {}
        for column in rule.columns:
            at_column = self._index[column]
            failures[column] = [
                at for at, row in enumerate(rows) if self._fails(rule, row[at_column])
            ]
        return failures

    def _fails(self, rule: _Rule, value: str) -> bool:
        if rule.check == "not-null":
            return value == ""
        if value == "":
            return False
        if rule.check == "type":
            return not (is_int(value) if rule.params[0] == "int" else is_date(value))
        if rule.check == "allowed":
            return value not in rule.params
        if rule.check == "range":
            return is_int(value) and not int(rule.params[0]) <= int(value) <= int(rule.params[1])
        return value not in self._dimensions[rule.params[0]]

    def _batch_failure(self, rule: _Rule, rows: list[list[str]]) -> str | None:
        """The observed value of a failing batch rule, or None when it passes."""
        if rule.check == "row-count":
            if self._previous is None:
                return None
            before, tolerance = len(self._previous), int(rule.params[0])
            low = before * (100 - tolerance) // 100
            high = -(-before * (100 + tolerance) // 100)
            return None if low <= len(rows) <= high else str(len(rows))
        column = self._index[rule.columns[0]]
        values = [int(row[column]) for row in rows if is_int(row[column])]
        if rule.check == "freshness":
            if not values:
                return "none"
            lag = self._now - max(values)
            return str(lag) if lag > int(rule.params[0]) else None
        if self._previous is None:
            return None
        baseline = [int(row[column]) for row in self._previous if is_int(row[column])]
        if not values or not baseline:
            return None
        edges = [int(edge) for edge in rule.params[1:]]
        units = math.floor(self._psi(values, baseline, edges) * 10000 + 0.5)
        if units < ten_thousandths(rule.params[0]):
            return None
        return f"{units // 10000}.{units % 10000:04d}"

    @staticmethod
    def _psi(values: list[int], baseline: list[int], edges: list[int]) -> float:
        def shares(sample: list[int]) -> list[float]:
            counts = [0] * (len(edges) + 1)
            for value in sample:
                counts[bisect_right(edges, value)] += 1
            return [count / len(sample) or EMPTY_SHARE for count in counts]

        actual, expected = shares(values), shares(baseline)
        # A plain loop, not sum(): since Python 3.12 sum() adds floats with a more accurate
        # algorithm, and the other languages add the terms one by one in bin order.
        total = 0.0
        for a, e in zip(actual, expected, strict=True):
            total += (a - e) * math.log(a / e)
        return total
