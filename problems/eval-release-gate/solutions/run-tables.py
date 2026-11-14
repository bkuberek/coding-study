import json
import re
from dataclasses import dataclass, field

TYPE_CHECKS = {"string", "int", "bool", "strings"}
WORD = re.compile(r"[a-z0-9]+")


def _reject_constant(name: str) -> None:
    raise ValueError(f"{name} is not JSON")


def parse_json(text: str) -> tuple[bool, object]:
    """Strict JSON: no NaN, no Infinity, nothing after the value."""
    try:
        return True, json.loads(text, parse_constant=_reject_constant)
    except ValueError:
        return False, None


def matches_type(value: object, kind: str) -> bool:
    if kind == "string":
        return isinstance(value, str)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        if isinstance(value, bool):
            return False
        return isinstance(value, int) or (isinstance(value, float) and value.is_integer())
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def half_up_mean(total: int, count: int) -> int:
    """The mean of whole scores in hundredths, ties rounded up."""
    return (200 * total + count) // (2 * count)


def floor_percent(part: int, whole: int) -> int:
    return 100 * part // whole if whole > 0 else 0


def kappa_thousandths(pairs: list[tuple[bool, bool]]) -> str:
    both = sum(1 for judge, human in pairs if judge and human)
    judge_only = sum(1 for judge, human in pairs if judge and not human)
    human_only = sum(1 for judge, human in pairs if human and not judge)
    neither = len(pairs) - both - judge_only - human_only
    count = len(pairs)
    chance = (both + judge_only) * (both + human_only) + (human_only + neither) * (
        judge_only + neither
    )
    numerator = count * (both + neither) - chance
    denominator = count * count - chance
    if denominator == 0:
        return "undefined"
    scaled = (2000 * abs(numerator) + denominator) // (2 * denominator)
    return str(-scaled if numerator < 0 else scaled)


@dataclass
class _Run:
    cases: dict[str, tuple[str, str]] = field(default_factory=dict)
    criteria: list[str] = field(default_factory=list)
    judge: dict[str, dict[str, int]] = field(default_factory=dict)
    human: dict[str, dict[str, int]] = field(default_factory=dict)


class ReleaseGate:
    def __init__(self) -> None:
        self._schema: list[tuple[str, str, bool]] = []
        self._banned: list[str] = []
        self._runs: dict[str, _Run] = {}
        self._critical: list[str] = []
        self._max_drop = 0

    # Level 1
    def set_schema(self, rows: list[list[str]]) -> None:
        self._schema = [(name, kind, requirement == "required") for name, kind, requirement in rows]

    def set_banned_words(self, words: list[str]) -> None:
        self._banned = list(words)

    def check(self, output: str) -> list[str]:
        codes: list[str] = []
        parsed, value = parse_json(output)
        if not parsed:
            codes.append("json")
        elif not isinstance(value, dict):
            codes.append("object")
        else:
            for name, kind, required in self._schema:
                if name not in value:
                    if required:
                        codes.append(f"missing:{name}")
                elif not matches_type(value[name], kind):
                    codes.append(f"type:{name}")
        present = set(WORD.findall(output.lower()))
        codes.extend(f"banned:{word}" for word in sorted(set(self._banned) & present))
        return codes

    def add_run(
        self, run: str, case_ids: list[str], inputs: list[str], outputs: list[str]
    ) -> int:
        table = _Run()
        for case_id, text, output in zip(case_ids, inputs, outputs, strict=True):
            table.cases[case_id] = (text, output)
        self._runs[run] = table
        return len(table.cases)

    def check_run(self, run: str) -> list[list[str]]:
        table = self._runs.get(run)
        if table is None:
            return []
        rows = []
        for case_id in sorted(table.cases):
            codes = self.check(table.cases[case_id][1])
            rows.append([case_id, "fail" if codes else "pass", *codes])
        return rows

    # Level 2
    def add_scores(
        self, run: str, criteria: list[str], case_ids: list[str], scores: list[list[int]]
    ) -> int:
        table = self._runs[run]
        table.criteria = list(criteria)
        table.judge = {
            case_id: dict(zip(criteria, row, strict=True))
            for case_id, row in zip(case_ids, scores, strict=True)
        }
        return len(case_ids)

    def add_human_scores(
        self, run: str, case_ids: list[str], criteria: list[str], scores: list[list[int]]
    ) -> int:
        table = self._runs[run]
        cells = 0
        for case_id, row in zip(case_ids, scores, strict=True):
            for criterion, score in zip(criteria, row, strict=True):
                table.human.setdefault(case_id, {})[criterion] = score
                cells += 1
        return cells

    def aggregate(self, run: str) -> list[list[str]]:
        table = self._runs.get(run)
        if table is None or not table.judge:
            return []
        rows = []
        grand_total = grand_count = grand_human = 0
        for criterion in sorted(table.criteria):
            scores = [self._effective(table, case_id, criterion) for case_id in table.judge]
            human = sum(1 for case_id in table.judge if criterion in table.human.get(case_id, {}))
            rows.append([criterion, str(half_up_mean(sum(scores), len(scores))), str(human)])
            grand_total += sum(scores)
            grand_count += len(scores)
            grand_human += human
        rows.append(["overall", str(half_up_mean(grand_total, grand_count)), str(grand_human)])
        return rows

    def agreement(self, run: str, pass_score: int) -> list[list[str]]:
        table = self._runs.get(run)
        if table is None:
            return []
        rows = []
        for criterion in sorted(table.criteria):
            pairs = self._verdict_pairs(table, criterion, pass_score)
            if not pairs:
                continue
            agreed = sum(1 for judge, human in pairs if judge == human)
            rows.append(
                [criterion, str(len(pairs)), str(floor_percent(agreed, len(pairs)))]
                + [kappa_thousandths(pairs)]
            )
        return rows

    def disagreements(self, run: str, pass_score: int) -> list[list[str]]:
        table = self._runs.get(run)
        if table is None:
            return []
        rows = []
        for case_id in sorted(table.human):
            for criterion in sorted(table.human[case_id]):
                judge = table.judge[case_id][criterion]
                human = table.human[case_id][criterion]
                if (judge >= pass_score) != (human >= pass_score):
                    rows.append([case_id, criterion, str(judge), str(human)])
        return rows

    # Level 3
    def compare(
        self, baseline_runs: list[str], candidate_runs: list[str], pass_score: int
    ) -> list[list[str]]:
        return [self._compare_row(case_id, baseline_runs, candidate_runs, pass_score)
                for case_id in self._golden(baseline_runs)]

    def summarize(
        self, baseline_runs: list[str], candidate_runs: list[str], pass_score: int
    ) -> list[int]:
        rows = self.compare(baseline_runs, candidate_runs, pass_score)
        return [
            sum(1 for row in rows if row[1] == "regression"),
            sum(1 for row in rows if row[1] == "improvement"),
            sum(1 for row in rows if row[1] == "same"),
            sum(1 for row in rows if row[2] == "pass->fail"),
            sum(1 for row in rows if row[2] == "fail->pass"),
        ]

    # Level 4
    def configure_gate(self, critical: list[str], max_drop: int) -> None:
        self._critical = list(critical)
        self._max_drop = max_drop

    def gate(
        self, baseline_runs: list[str], candidate_runs: list[str], pass_score: int
    ) -> list[list[str]]:
        reasons = self._assertion_reasons(candidate_runs)
        golden = self._golden(baseline_runs)
        rows = {
            row[0]: row for row in self.compare(baseline_runs, candidate_runs, pass_score)
        }
        for case_id in sorted(self._critical):
            row = rows.get(case_id)
            if row is not None and (row[1] == "regression" or row[2] == "pass->fail"):
                reasons.append(["reason", "critical", case_id, row[1], row[2]])
        before = self._quality(baseline_runs, golden)
        after = self._quality(candidate_runs, golden)
        if before - after > self._max_drop:
            reasons.append(
                ["reason", "quality", str(before), str(after), str(before - after)]
                + [str(self._max_drop)]
            )
        decision = "block" if reasons else "ship"
        proposals = self._proposals(golden, candidate_runs, pass_score)
        return [["decision", decision], *reasons, *proposals]

    # Helpers
    def _effective(self, table: _Run, case_id: str, criterion: str) -> int:
        human = table.human.get(case_id, {})
        return human[criterion] if criterion in human else table.judge[case_id][criterion]

    def _verdict_pairs(
        self, table: _Run, criterion: str, pass_score: int
    ) -> list[tuple[bool, bool]]:
        return [
            (table.judge[case_id][criterion] >= pass_score, cells[criterion] >= pass_score)
            for case_id, cells in sorted(table.human.items())
            if criterion in cells
        ]

    def _golden(self, baseline_runs: list[str]) -> list[str]:
        return sorted(self._runs[baseline_runs[0]].cases)

    def _case_score(self, run: str, case_id: str) -> int:
        table = self._runs[run]
        return sum(self._effective(table, case_id, criterion) for criterion in table.criteria)

    def _failure_codes(self, run: str, case_id: str, pass_score: int) -> list[str]:
        table = self._runs[run]
        codes = self.check(table.cases[case_id][1])
        if case_id in table.judge:
            low = [c for c in sorted(table.criteria) if self._effective(table, case_id, c) < pass_score]
            codes.extend(f"low:{criterion}" for criterion in low)
        return codes

    def _passes(self, run: str, case_id: str, pass_score: int) -> bool:
        return not self._failure_codes(run, case_id, pass_score)

    def _majority_passes(self, runs: list[str], case_id: str, pass_score: int) -> tuple[bool, int]:
        passed = sum(1 for run in runs if self._passes(run, case_id, pass_score))
        return 2 * passed > len(runs), passed

    def _compare_row(
        self, case_id: str, baseline_runs: list[str], candidate_runs: list[str], pass_score: int
    ) -> list[str]:
        before = [self._case_score(run, case_id) for run in baseline_runs]
        after = [self._case_score(run, case_id) for run in candidate_runs]
        if max(after) < min(before):
            change = "regression"
        elif min(after) > max(before):
            change = "improvement"
        else:
            change = "same"
        was, was_count = self._majority_passes(baseline_runs, case_id, pass_score)
        is_now, now_count = self._majority_passes(candidate_runs, case_id, pass_score)
        flip = "-"
        if was and not is_now:
            flip = "pass->fail"
        elif is_now and not was:
            flip = "fail->pass"
        return [
            case_id,
            change,
            flip,
            str(min(before)),
            str(max(before)),
            str(min(after)),
            str(max(after)),
            f"{was_count}/{len(baseline_runs)}",
            f"{now_count}/{len(candidate_runs)}",
        ]

    def _quality(self, runs: list[str], golden: list[str]) -> int:
        total = count = 0
        for run in runs:
            table = self._runs[run]
            for case_id in golden:
                for criterion in table.criteria:
                    total += self._effective(table, case_id, criterion)
                    count += 1
        return half_up_mean(total, count)

    def _assertion_reasons(self, candidate_runs: list[str]) -> list[list[str]]:
        reasons = []
        for run in candidate_runs:
            for case_id in sorted(self._runs[run].cases):
                codes = self.check(self._runs[run].cases[case_id][1])
                if codes:
                    reasons.append(["reason", "assertion", run, case_id, ",".join(codes)])
        return reasons

    def _proposals(
        self, golden: list[str], candidate_runs: list[str], pass_score: int
    ) -> list[list[str]]:
        fresh = sorted({c for run in candidate_runs for c in self._runs[run].cases} - set(golden))
        proposals = []
        for case_id in fresh:
            codes: set[str] = set()
            for run in candidate_runs:
                if case_id in self._runs[run].cases:
                    codes.update(self._failure_codes(run, case_id, pass_score))
            if codes:
                first = next(run for run in candidate_runs if case_id in self._runs[run].cases)
                text = self._runs[first].cases[case_id][0]
                proposals.append(["propose", case_id, text, ",".join(sorted(codes))])
        return proposals
