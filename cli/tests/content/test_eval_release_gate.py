"""eval-release-gate promises that its hidden cases catch the classic mistakes of a release gate for
a language-model change: a parser that is more lenient than JSON, a boolean taken for a number, a
banned word found inside another word or hidden behind an underscore, a mean that is rounded the
wrong way, a human score that does not replace the judge's, a kappa that is rounded, corrected or
left undefined wrongly, a noise rule that fires on touching ranges, a majority that counts a tie as
a pass, a flip confused with a change, a critical case that is judged by only one of its two
signals, a drop that is measured over the wrong cases, a threshold that blocks at equality, and a
proposal made for the wrong cases or with some of the reasons missing. These tests replay every case
against a model of the gate written from the statement, which must give every expected output, and
against that model with one mistake planted at a time, which some hidden case must fail. A mistake
that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from math import floor
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0327-eval-release-gate"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

HALF = Fraction(1, 2)


@dataclass
class Run:
    cases: dict[str, tuple[str, str]] = field(default_factory=dict)
    criteria: list[str] = field(default_factory=list)
    judge: dict[str, dict[str, int]] = field(default_factory=dict)
    human: dict[str, dict[str, int]] = field(default_factory=dict)


class Model:
    """The gate as the statement words it. Every answer is found by looking at the tables of the
    runs, so each mistake below overrides a single rule."""

    def __init__(self) -> None:
        self.schema: list[list[str]] = []
        self.banned: list[str] = []
        self.runs: dict[str, Run] = {}
        self.critical: list[str] = []
        self.max_drop = 0

    # --- level 1: JSON
    def prepare(self, text: str) -> str:
        return text

    def constant(self, name: str) -> float:
        raise ValueError(name)

    def pairs(self, items: list[tuple[str, Any]]) -> dict[str, Any]:
        return dict(items)

    def parse(self, text: str) -> tuple[bool, Any]:
        try:
            value = json.loads(
                self.prepare(text), parse_constant=self.constant, object_pairs_hook=self.pairs
            )
        except ValueError:
            return False, None
        return True, value

    def not_json_code(self) -> str:
        return "json"

    def not_object_code(self) -> str:
        return "object"

    # --- level 1: fields
    def is_int(self, value: Any) -> bool:
        if isinstance(value, bool):
            return False
        return isinstance(value, int | float) and float(value).is_integer()

    def is_strings(self, value: Any) -> bool:
        return isinstance(value, list) and all(isinstance(item, str) for item in value)

    def has_type(self, value: Any, kind: str) -> bool:
        if kind == "string":
            return isinstance(value, str)
        if kind == "bool":
            return isinstance(value, bool)
        if kind == "int":
            return self.is_int(value)
        return self.is_strings(value)

    def schema_rows(self) -> list[list[str]]:
        return self.schema

    def counts_as_absent(self, value: Any) -> bool:
        return False

    def reports_missing(self, requirement: str) -> bool:
        return requirement == "required"

    def field_reasons(self, value: dict[str, Any]) -> list[str]:
        reasons = []
        for name, kind, requirement in self.schema_rows():
            if name not in value or self.counts_as_absent(value[name]):
                if self.reports_missing(requirement):
                    reasons.append(f"missing:{name}")
            elif not self.has_type(value[name], kind):
                reasons.append(f"type:{name}")
        return reasons

    # --- level 1: words
    def word_pattern(self) -> str:
        return r"[a-z0-9]+"

    def text_for_words(self, output: str) -> str:
        return output.lower()

    def is_banned(self, word: str, words: set[str], text: str) -> bool:
        return word in words

    def banned_reasons(self, output: str) -> list[str]:
        text = self.text_for_words(output)
        words = set(re.findall(self.word_pattern(), text))
        found = sorted({word for word in self.banned if self.is_banned(word, words, text)})
        return [f"banned:{word}" for word in found]

    def arrange(self, head: list[str], banned: list[str]) -> list[str]:
        return head + banned

    def check(self, output: str) -> list[str]:
        parsed, value = self.parse(output)
        head: list[str] = []
        if not parsed:
            head.append(self.not_json_code())
        elif not isinstance(value, dict):
            head.append(self.not_object_code())
        else:
            head.extend(self.field_reasons(value))
        return self.arrange(head, self.banned_reasons(output))

    def set_schema(self, rows: list[list[str]]) -> None:
        self.schema = [list(row) for row in rows]

    def set_banned_words(self, words: list[str]) -> None:
        self.banned = list(words)

    def store_run(self, name: str, table: Run) -> None:
        self.runs[name] = table

    def add_run(self, run: str, case_ids: list[str], inputs: list[str], outputs: list[str]) -> int:
        table = Run()
        for case_id, text, output in zip(case_ids, inputs, outputs, strict=True):
            table.cases[case_id] = (text, output)
        self.store_run(run, table)
        return len(table.cases)

    def ordered(self, ids: Sequence[str]) -> list[str]:
        return sorted(ids)

    def check_run(self, run: str) -> list[list[str]]:
        if run not in self.runs:
            return []
        table = self.runs[run]
        rows = []
        for case_id in self.ordered(list(table.cases)):
            reasons = self.check(table.cases[case_id][1])
            rows.append([case_id, "fail" if reasons else "pass", *reasons])
        return rows

    # --- level 2
    def add_scores(
        self, run: str, criteria: list[str], case_ids: list[str], scores: list[list[int]]
    ) -> int:
        table = self.runs[run]
        table.criteria = list(criteria)
        table.judge = {
            case_id: dict(zip(criteria, row, strict=True))
            for case_id, row in zip(case_ids, scores, strict=True)
        }
        self.after_scores(table)
        return len(case_ids)

    def after_scores(self, table: Run) -> None:
        return None

    def keep_human(self, old: int | None, new: int) -> int:
        return new

    def human_count(self, set_cells: int, new_cells: int) -> int:
        return set_cells

    def add_human_scores(
        self, run: str, case_ids: list[str], criteria: list[str], scores: list[list[int]]
    ) -> int:
        table = self.runs[run]
        set_cells = new_cells = 0
        for case_id, row in zip(case_ids, scores, strict=True):
            for criterion, score in zip(criteria, row, strict=True):
                cells = table.human.setdefault(case_id, {})
                new_cells += criterion not in cells
                cells[criterion] = self.keep_human(cells.get(criterion), score)
                set_cells += 1
        return self.human_count(set_cells, new_cells)

    def effective(self, table: Run, case_id: str, criterion: str) -> int:
        human = table.human.get(case_id, {})
        return human[criterion] if criterion in human else table.judge[case_id][criterion]

    def round_mean(self, value: Fraction) -> int:
        return floor(value + HALF)

    def mean(self, scores: list[int]) -> int:
        return self.round_mean(Fraction(100 * sum(scores), len(scores)))

    def criterion_order(self, criteria: list[str]) -> list[str]:
        return sorted(criteria)

    def human_cells(self, table: Run, criterion: str) -> int:
        return sum(1 for case_id in table.judge if criterion in table.human.get(case_id, {}))

    def overall(self, table: Run, per_criterion: list[int]) -> int:
        return self.mean([self.effective(table, c, k) for c in table.judge for k in table.criteria])

    def aggregate(self, run: str) -> list[list[str]]:
        table = self.runs.get(run)
        if table is None or not table.judge:
            return []
        rows = []
        means = []
        for criterion in self.criterion_order(table.criteria):
            scores = [self.effective(table, case_id, criterion) for case_id in table.judge]
            means.append(self.mean(scores))
            rows.append([criterion, str(means[-1]), str(self.human_cells(table, criterion))])
        human_total = sum(int(row[2]) for row in rows)
        rows.append(["overall", str(self.overall(table, means)), str(human_total)])
        return rows

    def judge_side(self, table: Run, case_id: str, criterion: str) -> int:
        return table.judge[case_id][criterion]

    def passed(self, score: int, pass_score: int) -> bool:
        return score >= pass_score

    def labelled_cases(self, table: Run, criterion: str) -> list[str]:
        return sorted(c for c, cells in table.human.items() if criterion in cells)

    def pairs_of(self, table: Run, criterion: str, pass_score: int) -> list[tuple[bool, bool]]:
        return [
            (
                self.passed(self.judge_side(table, case_id, criterion), pass_score),
                self.passed(table.human[case_id][criterion], pass_score),
            )
            for case_id in self.labelled_cases(table, criterion)
        ]

    def agree_percent(self, agreed: int, total: int) -> int:
        return 100 * agreed // total

    def chance(self, a: int, b: int, c: int, d: int) -> Fraction:
        n = a + b + c + d
        return Fraction((a + b) * (a + c) + (c + d) * (b + d), n * n)

    def round_thousandths(self, value: Fraction) -> int:
        magnitude = floor(abs(value) + HALF)
        return -magnitude if value < 0 else magnitude

    def undefined(self) -> str:
        return "undefined"

    def kappa(self, pairs: list[tuple[bool, bool]]) -> str:
        a = sum(1 for j, h in pairs if j and h)
        b = sum(1 for j, h in pairs if j and not h)
        c = sum(1 for j, h in pairs if h and not j)
        d = len(pairs) - a - b - c
        chance = self.chance(a, b, c, d)
        if chance == 1:
            return self.undefined()
        observed = Fraction(a + d, len(pairs))
        return str(self.round_thousandths(1000 * (observed - chance) / (1 - chance)))

    def agreement(self, run: str, pass_score: int) -> list[list[str]]:
        table = self.runs.get(run)
        if table is None:
            return []
        rows = []
        for criterion in sorted(table.criteria):
            pairs = self.pairs_of(table, criterion, pass_score)
            if not pairs:
                continue
            agreed = sum(1 for judge, human in pairs if judge == human)
            percent = self.agree_percent(agreed, len(pairs))
            rows.append([criterion, str(len(pairs)), str(percent), self.kappa(pairs)])
        return rows

    def differs(self, judge: int, human: int, pass_score: int) -> bool:
        return self.passed(judge, pass_score) != self.passed(human, pass_score)

    def disagreement_order(self, table: Run) -> list[str]:
        return sorted(table.human)

    def disagreements(self, run: str, pass_score: int) -> list[list[str]]:
        table = self.runs.get(run)
        if table is None:
            return []
        rows = []
        for case_id in self.disagreement_order(table):
            for criterion in sorted(table.human[case_id]):
                judge = table.judge[case_id][criterion]
                human = table.human[case_id][criterion]
                if self.differs(judge, human, pass_score):
                    rows.append([case_id, criterion, str(judge), str(human)])
        return rows

    # --- level 3
    def case_score(self, run: str, case_id: str) -> int:
        table = self.runs[run]
        return sum(self.effective(table, case_id, criterion) for criterion in table.criteria)

    def verdict_score(self, table: Run, case_id: str, criterion: str) -> int:
        return self.effective(table, case_id, criterion)

    def assertion_reasons(self, run: str, case_id: str) -> list[str]:
        return self.check(self.runs[run].cases[case_id][1])

    def low_reasons(self, run: str, case_id: str, pass_score: int) -> list[str]:
        table = self.runs[run]
        if case_id not in table.judge:
            return []
        return [
            f"low:{criterion}"
            for criterion in sorted(table.criteria)
            if not self.passed(self.verdict_score(table, case_id, criterion), pass_score)
        ]

    def reasons_of(self, run: str, case_id: str, pass_score: int) -> list[str]:
        return self.assertion_reasons(run, case_id) + self.low_reasons(run, case_id, pass_score)

    def passes_in(self, runs: list[str], case_id: str, pass_score: int) -> int:
        return sum(1 for run in runs if not self.reasons_of(run, case_id, pass_score))

    def side_passes(self, passes: int, runs: int) -> bool:
        return 2 * passes > runs

    def golden(self, baseline: list[str]) -> list[str]:
        return self.ordered(list(self.runs[baseline[0]].cases))

    def change(self, before: list[int], after: list[int]) -> str:
        if max(after) < min(before):
            return "regression"
        if min(after) > max(before):
            return "improvement"
        return "same"

    def flip(self, was: bool, now: bool, change: str) -> str:
        if was and not now:
            return "pass->fail"
        if now and not was:
            return "fail->pass"
        return "-"

    def baseline_scores(self, baseline: list[str], case_id: str) -> list[int]:
        return [self.case_score(run, case_id) for run in baseline]

    def row(
        self, case_id: str, baseline: list[str], candidate: list[str], pass_score: int
    ) -> list[str]:
        before = self.baseline_scores(baseline, case_id)
        after = [self.case_score(run, case_id) for run in candidate]
        was_count = self.passes_in(baseline, case_id, pass_score)
        now_count = self.passes_in(candidate, case_id, pass_score)
        change = self.change(before, after)
        flip = self.flip(
            self.side_passes(was_count, len(baseline)),
            self.side_passes(now_count, len(candidate)),
            change,
        )
        return [
            case_id,
            change,
            flip,
            str(min(before)),
            str(max(before)),
            str(min(after)),
            str(max(after)),
            f"{was_count}/{len(baseline)}",
            f"{now_count}/{len(candidate)}",
        ]

    def cases_compared(self, baseline: list[str], candidate: list[str]) -> list[str]:
        return self.golden(baseline)

    def compare(
        self, baseline: list[str], candidate: list[str], pass_score: int
    ) -> list[list[str]]:
        return [
            self.row(case_id, baseline, candidate, pass_score)
            for case_id in self.cases_compared(baseline, candidate)
        ]

    def regressions(self, rows: list[list[str]]) -> int:
        return sum(1 for row in rows if row[1] == "regression")

    def summarize(self, baseline: list[str], candidate: list[str], pass_score: int) -> list[int]:
        rows = self.compare(baseline, candidate, pass_score)
        return [
            self.regressions(rows),
            sum(1 for row in rows if row[1] == "improvement"),
            sum(1 for row in rows if row[1] == "same"),
            sum(1 for row in rows if row[2] == "pass->fail"),
            sum(1 for row in rows if row[2] == "fail->pass"),
        ]

    # --- level 4
    def set_gate(self, critical: list[str], max_drop: int) -> None:
        self.critical = list(critical)
        self.max_drop = max_drop

    def configure_gate(self, critical: list[str], max_drop: int) -> None:
        self.set_gate(critical, max_drop)

    def quality_cases(self, runs: list[str], golden: list[str]) -> list[str]:
        return golden

    def quality_runs(self, runs: list[str]) -> list[str]:
        return runs

    def quality(self, runs: list[str], golden: list[str]) -> int:
        scores = []
        for run in self.quality_runs(runs):
            table = self.runs[run]
            for case_id in self.quality_cases(runs, golden):
                scores.extend(self.effective(table, case_id, k) for k in table.criteria)
        return self.mean(scores)

    def assertion_runs(self, candidate: list[str]) -> list[str]:
        return candidate

    def assertion_cases(self, run: str, golden: list[str]) -> list[str]:
        return self.ordered(list(self.runs[run].cases))

    def assertion_rows(self, candidate: list[str], golden: list[str]) -> list[list[str]]:
        rows = []
        for run in self.assertion_runs(candidate):
            for case_id in self.assertion_cases(run, golden):
                reasons = self.assertion_reasons(run, case_id)
                if reasons:
                    rows.append(["reason", "assertion", run, case_id, ",".join(reasons)])
        return rows

    def critical_order(self) -> list[str]:
        return sorted(self.critical)

    def is_critical_regression(self, row: list[str]) -> bool:
        return row[1] == "regression" or row[2] == "pass->fail"

    def critical_rows(self, compared: list[list[str]]) -> list[list[str]]:
        by_case = {row[0]: row for row in compared}
        return [
            ["reason", "critical", case_id, by_case[case_id][1], by_case[case_id][2]]
            for case_id in self.critical_order()
            if case_id in by_case and self.is_critical_regression(by_case[case_id])
        ]

    def too_much(self, drop: int) -> bool:
        return drop > self.max_drop

    def drop_of(self, before: int, after: int) -> int:
        return before - after

    def quality_rows(
        self, baseline: list[str], candidate: list[str], golden: list[str]
    ) -> list[list[str]]:
        before = self.quality(baseline, golden)
        after = self.quality(candidate, golden)
        drop = self.drop_of(before, after)
        if not self.too_much(drop):
            return []
        return [["reason", "quality", str(before), str(after), str(drop), str(self.max_drop)]]

    def needs_proposal(self, reasons: list[str]) -> bool:
        return bool(reasons)

    def proposal_reasons(self, runs: list[str], case_id: str, pass_score: int) -> list[str]:
        found: set[str] = set()
        for run in runs:
            if case_id in self.runs[run].cases:
                found.update(self.reasons_of(run, case_id, pass_score))
        return sorted(found)

    def new_cases(self, candidate: list[str], golden: list[str]) -> list[str]:
        names = {case for run in candidate for case in self.runs[run].cases}
        return sorted(names - set(golden))

    def proposal_rows(
        self, candidate: list[str], golden: list[str], pass_score: int
    ) -> list[list[str]]:
        rows = []
        for case_id in self.new_cases(candidate, golden):
            reasons = self.proposal_reasons(candidate, case_id, pass_score)
            if self.needs_proposal(reasons):
                run = next(r for r in candidate if case_id in self.runs[r].cases)
                rows.append(
                    ["propose", case_id, self.runs[run].cases[case_id][0], ",".join(reasons)]
                )
        return rows

    def decide(self, reasons: list[list[str]]) -> str:
        return "block" if reasons else "ship"

    def order_reasons(
        self, assertions: list[list[str]], critical: list[list[str]], quality: list[list[str]]
    ) -> list[list[str]]:
        return assertions + critical + quality

    def gate(self, baseline: list[str], candidate: list[str], pass_score: int) -> list[list[str]]:
        golden = self.golden(baseline)
        compared = self.compare(baseline, candidate, pass_score)
        reasons = self.order_reasons(
            self.assertion_rows(candidate, golden),
            self.critical_rows(compared),
            self.quality_rows(baseline, candidate, golden),
        )
        proposals = self.proposal_rows(candidate, golden, pass_score)
        return [["decision", self.decide(reasons)], *reasons, *proposals]


# ------------------------------------------------------------------ level 1 mistakes
class AcceptsATrailingComma(Model):
    """Reads a list or an object that ends with a comma."""

    def prepare(self, text: str) -> str:
        return re.sub(r",(\s*[}\]])", r"\1", text)


class AcceptsSingleQuotes(Model):
    """Reads a text written with single quotes."""

    def prepare(self, text: str) -> str:
        return text.replace("'", '"')


class AcceptsNaNAndInfinity(Model):
    """Reads the constants that JSON does not have."""

    def constant(self, name: str) -> float:
        return float("nan") if name == "NaN" else float("inf")


class FindsJsonInsideText(Model):
    """Looks for an object inside the text around it."""

    def prepare(self, text: str) -> str:
        found = re.search(r"\{.*\}", text, re.DOTALL)
        return found.group(0) if found else text


class IgnoresTextAfterTheValue(Model):
    """Reads one value and ignores what follows it."""

    def parse(self, text: str) -> tuple[bool, Any]:
        try:
            decoder = json.JSONDecoder(parse_constant=self.constant, object_pairs_hook=self.pairs)
            value, _ = decoder.raw_decode(text.lstrip())
        except ValueError:
            return False, None
        return True, value


class NotAnObjectIsNotJson(Model):
    """Gives the reason json when the value is a list or a scalar."""

    def not_object_code(self) -> str:
        return "json"


class NotAnObjectStillMissesFields(Model):
    """Lists the required fields as missing when the value is not an object."""

    def check(self, output: str) -> list[str]:
        reasons = super().check(output)
        if "object" in reasons:
            required = [f"missing:{n}" for n, _, q in self.schema if q == "required"]
            return [reasons[0], *required, *reasons[1:]]
        return reasons


class BooleanIsANumber(Model):
    """Lets true and false pass as whole numbers."""

    def is_int(self, value: Any) -> bool:
        return isinstance(value, int | float) and float(value).is_integer()


class WholeNumberMustHaveNoFraction(Model):
    """Refuses 3.0 and 1e2, which are whole numbers."""

    def is_int(self, value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)


class OptionalFieldIsReportedMissing(Model):
    """Reports an absent optional field."""

    def reports_missing(self, requirement: str) -> bool:
        return True


class NullIsMissing(Model):
    """Treats a field set to null as if it were not there."""

    def counts_as_absent(self, value: Any) -> bool:
        return value is None


class NullPassesAnyType(Model):
    """Lets null stand in for any type."""

    def has_type(self, value: Any, kind: str) -> bool:
        return value is None or super().has_type(value, kind)


class FieldReasonsFollowTheNames(Model):
    """Lists the fields in alphabetical order and not in the order of the schema."""

    def schema_rows(self) -> list[list[str]]:
        return sorted(self.schema)


class ExtraFieldsAreReported(Model):
    """Adds a reason for a field the schema does not name."""

    def field_reasons(self, value: dict[str, Any]) -> list[str]:
        known = {row[0] for row in self.schema}
        extra = [f"extra:{name}" for name in value if name not in known]
        return super().field_reasons(value) + extra


class StringsAcceptsAnyList(Model):
    """Does not look at the items of a list."""

    def is_strings(self, value: Any) -> bool:
        return isinstance(value, list)


class StringsMustNotBeEmpty(Model):
    """Refuses an empty list."""

    def is_strings(self, value: Any) -> bool:
        return bool(value) and super().is_strings(value)


class FirstOfTwoEqualNamesCounts(Model):
    """Keeps the first value of a name that appears twice."""

    def pairs(self, items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in items:
            result.setdefault(name, value)
        return result


class BannedWordInsideAWord(Model):
    """Looks for the banned word anywhere in the text."""

    def is_banned(self, word: str, words: set[str], text: str) -> bool:
        return word in text


class BannedWordIsCaseSensitive(Model):
    """Looks for the banned word in the text as written."""

    def text_for_words(self, output: str) -> str:
        return output

    def is_banned(self, word: str, words: set[str], text: str) -> bool:
        return word in words


class UnderscoreIsPartOfAWord(Model):
    """Counts the underscore as a letter."""

    def word_pattern(self) -> str:
        return r"[a-z0-9_]+"


class BannedWordsInTheValuesOnly(Model):
    """Reads the words of the decoded text values and not of the raw text."""

    def text_for_words(self, output: str) -> str:
        parsed, value = self.parse(output)
        if not parsed:
            return output.lower()
        strings: list[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, str):
                strings.append(node)
            elif isinstance(node, list):
                for item in node:
                    walk(item)
            elif isinstance(node, dict):
                for item in node.values():
                    walk(item)

        walk(value)
        return " ".join(strings).lower()


class BannedWordsInOrderOfAppearance(Model):
    """Lists the banned words as they come, one for each time."""

    def banned_reasons(self, output: str) -> list[str]:
        text = output.lower()
        hits = [(m.start(), m.group(0)) for m in re.finditer(r"[a-z0-9]+", text)]
        return [f"banned:{word}" for _, word in sorted(hits) if word in self.banned]


class BannedWordsIgnoredWhenNotJson(Model):
    """Looks for banned words only in a text that is JSON."""

    def check(self, output: str) -> list[str]:
        reasons = super().check(output)
        return [] if reasons[:1] == ["json"] else reasons


class BannedWordsComeFirst(Model):
    """Puts the banned words before the other reasons."""

    def arrange(self, head: list[str], banned: list[str]) -> list[str]:
        return banned + head


class RunRowsInOrderOfStoring(Model):
    """Reports the cases as they were stored."""

    def ordered(self, ids: Sequence[str]) -> list[str]:
        return list(ids)


class RunRowsInNaturalOrder(Model):
    """Puts case_2 before case_10."""

    def ordered(self, ids: Sequence[str]) -> list[str]:
        def natural(text: str) -> list[Any]:
            return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text)]

        return sorted(ids, key=natural)


class RunIsMergedIntoTheOldOne(Model):
    """Adds the cases to a run of the same name instead of replacing it."""

    def store_run(self, name: str, table: Run) -> None:
        if name in self.runs:
            self.runs[name].cases.update(table.cases)
        else:
            self.runs[name] = table


class SchemaIsAppended(Model):
    """Adds the rows to the ones that are there."""

    def set_schema(self, rows: list[list[str]]) -> None:
        self.schema = self.schema + [list(row) for row in rows]


class BannedWordsAreAppended(Model):
    """Adds the words to the ones that are there."""

    def set_banned_words(self, words: list[str]) -> None:
        self.banned = self.banned + list(words)


# ------------------------------------------------------------------ level 2 mistakes
class MeanIsRoundedDown(Model):
    """Cuts the mean to the hundredth below."""

    def round_mean(self, value: Fraction) -> int:
        return floor(value)


class MeanTiesGoToEven(Model):
    """Rounds a tie to the even hundredth."""

    def round_mean(self, value: Fraction) -> int:
        return round(value)


class MeanIgnoresHumans(Model):
    """Averages the judge's scores only."""

    def effective(self, table: Run, case_id: str, criterion: str) -> int:
        return table.judge[case_id][criterion]


class HumanCellsCountsTheCases(Model):
    """Counts the cases that have any human score, for every criterion."""

    def human_cells(self, table: Run, criterion: str) -> int:
        return sum(1 for case_id in table.judge if table.human.get(case_id))


class OverallIsTheMeanOfTheMeans(Model):
    """Averages the rounded means of the criteria."""

    def overall(self, table: Run, per_criterion: list[int]) -> int:
        return self.round_mean(Fraction(sum(per_criterion), len(per_criterion)))


class CriteriaInTheOrderGiven(Model):
    """Lists the criteria as they were given."""

    def criterion_order(self, criteria: list[str]) -> list[str]:
        return list(criteria)


class AgreementUsesTheEffectiveScore(Model):
    """Compares the human score with the score that already includes it."""

    def judge_side(self, table: Run, case_id: str, criterion: str) -> int:
        return self.effective(table, case_id, criterion)


class AgreementCountsEveryCase(Model):
    """Counts a case that no human scored as an agreement."""

    def pairs_of(self, table: Run, criterion: str, pass_score: int) -> list[tuple[bool, bool]]:
        found = super().pairs_of(table, criterion, pass_score)
        if not found:
            return found
        unscored = [(True, True)] * (len(table.judge) - len(found))
        return found + unscored


class AgreementPercentIsRounded(Model):
    """Rounds the percent to the nearest."""

    def agree_percent(self, agreed: int, total: int) -> int:
        return (200 * agreed + total) // (2 * total)


class KappaTiesGoUp(Model):
    """Rounds a tie upward, also for a negative kappa."""

    def round_thousandths(self, value: Fraction) -> int:
        return floor(value + HALF)


class KappaTiesGoToEven(Model):
    """Rounds a tie to the even thousandth."""

    def round_thousandths(self, value: Fraction) -> int:
        return round(value)


class KappaIsTruncated(Model):
    """Cuts the decimals off."""

    def round_thousandths(self, value: Fraction) -> int:
        return int(value)


class UndefinedKappaIsZero(Model):
    """Says no agreement beyond chance when chance explains everything."""

    def undefined(self) -> str:
        return "0"


class UndefinedKappaIsPerfect(Model):
    """Says perfect agreement when both said the same thing every time."""

    def undefined(self) -> str:
        return "1000"


class ChanceUsesTheJudgeTwice(Model):
    """Takes the chance of agreement from the judge's shares only."""

    def chance(self, a: int, b: int, c: int, d: int) -> Fraction:
        n = a + b + c + d
        return Fraction((a + b) ** 2 + (c + d) ** 2, n * n)


class PassScoreIsExclusive(Model):
    """Needs more than the pass score to pass."""

    def passed(self, score: int, pass_score: int) -> bool:
        return score > pass_score


class DisagreementIsAnyDifferenceOfScore(Model):
    """Lists the cells where the two scores differ at all."""

    def differs(self, judge: int, human: int, pass_score: int) -> bool:
        return judge != human


class DisagreementsInOrderOfLabelling(Model):
    """Lists the cases in the order the humans were added."""

    def disagreement_order(self, table: Run) -> list[str]:
        return list(table.human)


class FirstHumanScoreStays(Model):
    """Keeps the first human score of a cell."""

    def keep_human(self, old: int | None, new: int) -> int:
        return new if old is None else old


class NewJudgeScoresClearTheHumans(Model):
    """Forgets the human scores when the judge's are stored again."""

    def after_scores(self, table: Run) -> None:
        table.human = {}


class HumanCountIsNewCellsOnly(Model):
    """Returns the number of cells that had no human score before."""

    def human_count(self, set_cells: int, new_cells: int) -> int:
        return new_cells


# ------------------------------------------------------------------ level 3 mistakes
class ChangeComparesTheMeans(Model):
    """Compares the average score of each side."""

    def change(self, before: list[int], after: list[int]) -> str:
        left, right = Fraction(sum(before), len(before)), Fraction(sum(after), len(after))
        return "regression" if right < left else "improvement" if right > left else "same"


class TouchingRangesAreAChange(Model):
    """Calls it a change when the ranges only touch."""

    def change(self, before: list[int], after: list[int]) -> str:
        if max(after) <= min(before):
            return "regression"
        return "improvement" if min(after) >= max(before) else "same"


class ChangeUsesTheFirstRunOfEachSide(Model):
    """Looks at one run on each side."""

    def change(self, before: list[int], after: list[int]) -> str:
        return super().change(before[:1], after[:1])


class ChangeUsesTheWorstOfBothSides(Model):
    """Compares the worst runs of each side."""

    def change(self, before: list[int], after: list[int]) -> str:
        return super().change([min(before)], [min(after)])


class AnyHigherCandidateIsAnImprovement(Model):
    """Calls it an improvement when the best candidate run beats the best baseline run."""

    def change(self, before: list[int], after: list[int]) -> str:
        if max(after) < min(before):
            return "regression"
        return "improvement" if max(after) > max(before) else "same"


class HalfThePassesIsAPass(Model):
    """Counts half of the runs as enough."""

    def side_passes(self, passes: int, runs: int) -> bool:
        return 2 * passes >= runs


class AllRunsMustPass(Model):
    """Needs every run to pass."""

    def side_passes(self, passes: int, runs: int) -> bool:
        return passes == runs


class AnyPassingRunIsAPass(Model):
    """Needs one run to pass."""

    def side_passes(self, passes: int, runs: int) -> bool:
        return passes > 0


class VerdictIgnoresAssertions(Model):
    """Judges a case by its scores only."""

    def assertion_reasons(self, run: str, case_id: str) -> list[str]:
        return []


class VerdictIgnoresScores(Model):
    """Judges a case by its assertions only."""

    def low_reasons(self, run: str, case_id: str, pass_score: int) -> list[str]:
        return []


class VerdictUsesTheJudgeNotTheHuman(Model):
    """Looks at the judge's score even when a human gave one."""

    def verdict_score(self, table: Run, case_id: str, criterion: str) -> int:
        return table.judge[case_id][criterion]


class ScoreOfACaseIgnoresHumans(Model):
    """Adds the judge's scores only."""

    def case_score(self, run: str, case_id: str) -> int:
        table = self.runs[run]
        return sum(table.judge[case_id][criterion] for criterion in table.criteria)


class FlipOnlyWhenTheScoreChanged(Model):
    """Reports a flip only when the change is not the same."""

    def flip(self, was: bool, now: bool, change: str) -> str:
        return super().flip(was, now, change) if change != "same" else "-"


class ChangeOnlyWhenTheVerdictFlipped(Model):
    """Reports a change only for a flip."""

    def row(
        self, case_id: str, baseline: list[str], candidate: list[str], pass_score: int
    ) -> list[str]:
        row = super().row(case_id, baseline, candidate, pass_score)
        if row[2] == "-":
            row[1] = "same"
        return row


class CompareAlsoListsNewCases(Model):
    """Adds the cases only the candidate has."""

    def cases_compared(self, baseline: list[str], candidate: list[str]) -> list[str]:
        return sorted(set(self.golden(baseline)) | set(self.runs[candidate[0]].cases))


class CompareRowsInOrderOfStoring(Model):
    """Lists the cases in the order of the first baseline run."""

    def golden(self, baseline: list[str]) -> list[str]:
        return list(self.runs[baseline[0]].cases)


class SummaryCountsFlipsAsRegressions(Model):
    """Counts a flip to fail as a regression."""

    def regressions(self, rows: list[list[str]]) -> int:
        return sum(1 for row in rows if row[1] == "regression" or row[2] == "pass->fail")


class BaselineColumnsUseTheFirstRun(Model):
    """Reports the first run of the baseline as its min and max."""

    def baseline_scores(self, baseline: list[str], case_id: str) -> list[int]:
        return [self.case_score(baseline[0], case_id)] * len(baseline)


# ------------------------------------------------------------------ level 4 mistakes
class DropEqualToTheThresholdBlocks(Model):
    """Blocks at the threshold itself."""

    def too_much(self, drop: int) -> bool:
        return drop >= self.max_drop


class AnyChangeInQualityBlocks(Model):
    """Blocks when quality moves in either direction by more than the threshold."""

    def too_much(self, drop: int) -> bool:
        return abs(drop) > self.max_drop


class QualityIsRoundedDown(Model):
    """Cuts the mean at the hundredth."""

    def round_mean(self, value: Fraction) -> int:
        return floor(value)


class QualityCountsNewCases(Model):
    """Includes the cases the golden set does not have."""

    def quality_cases(self, runs: list[str], golden: list[str]) -> list[str]:
        return sorted({case for run in runs for case in self.runs[run].cases})


class QualityUsesTheFirstRunOfASide(Model):
    """Averages one run of each side."""

    def quality_runs(self, runs: list[str]) -> list[str]:
        return runs[:1]


class QualityIgnoresHumans(Model):
    """Uses the judge's scores only."""

    def effective(self, table: Run, case_id: str, criterion: str) -> int:
        return table.judge[case_id][criterion]


class DropIsMeasuredBackwards(Model):
    """Subtracts the baseline from the candidate."""

    def drop_of(self, before: int, after: int) -> int:
        return after - before


class CriticalCaseBlocksByChangeOnly(Model):
    """Ignores a flip of the verdict."""

    def is_critical_regression(self, row: list[str]) -> bool:
        return row[1] == "regression"


class CriticalCaseBlocksByFlipOnly(Model):
    """Ignores a drop in score."""

    def is_critical_regression(self, row: list[str]) -> bool:
        return row[2] == "pass->fail"


class CriticalCasesInTheOrderGiven(Model):
    """Lists the critical cases as they were configured."""

    def critical_order(self) -> list[str]:
        return list(self.critical)


class EveryRegressionBlocks(Model):
    """Blocks for a regression on any case and not only on the critical ones."""

    def critical_rows(self, compared: list[list[str]]) -> list[list[str]]:
        return [
            ["reason", "critical", row[0], row[1], row[2]]
            for row in compared
            if self.is_critical_regression(row)
        ]


class AssertionsOfTheGoldenCasesOnly(Model):
    """Checks the assertions on the cases of the golden set."""

    def assertion_cases(self, run: str, golden: list[str]) -> list[str]:
        return [case for case in super().assertion_cases(run, golden) if case in golden]


class AssertionsOfTheFirstCandidateRunOnly(Model):
    """Checks the assertions of the first candidate run."""

    def assertion_runs(self, candidate: list[str]) -> list[str]:
        return candidate[:1]


class AssertionRunsInTheOrderOfTheirNames(Model):
    """Lists the runs by name and not in the order given."""

    def assertion_runs(self, candidate: list[str]) -> list[str]:
        return sorted(candidate)


class AssertionsDoNotBlock(Model):
    """Leaves the assertion reasons out of the decision."""

    def decide(self, reasons: list[list[str]]) -> str:
        return "block" if any(row[1] != "assertion" for row in reasons) else "ship"


class QualityReasonsComeFirst(Model):
    """Lists the quality before the assertions."""

    def order_reasons(
        self, assertions: list[list[str]], critical: list[list[str]], quality: list[list[str]]
    ) -> list[list[str]]:
        return quality + critical + assertions


class CriticalReasonsComeFirst(Model):
    """Lists the critical cases before the assertions."""

    def order_reasons(
        self, assertions: list[list[str]], critical: list[list[str]], quality: list[list[str]]
    ) -> list[list[str]]:
        return critical + assertions + quality


class NewCaseThatFailsOnAScoreBlocks(Model):
    """Lets a low score on a new case block the release."""

    def gate(self, baseline: list[str], candidate: list[str], pass_score: int) -> list[list[str]]:
        rows = super().gate(baseline, candidate, pass_score)
        if any(row[0] == "propose" and "low:" in row[3] for row in rows):
            rows[0] = ["decision", "block"]
        return rows


class GoldenCasesThatFailAreProposed(Model):
    """Proposes every case that fails, also those the golden set holds."""

    def new_cases(self, candidate: list[str], golden: list[str]) -> list[str]:
        return sorted({case for run in candidate for case in self.runs[run].cases})


class ProposalsForAssertionsOnly(Model):
    """Proposes a new case for an assertion that failed and not for a low score."""

    def proposal_reasons(self, runs: list[str], case_id: str, pass_score: int) -> list[str]:
        found: set[str] = set()
        for run in runs:
            if case_id in self.runs[run].cases:
                found.update(self.assertion_reasons(run, case_id))
        return sorted(found)


class ProposalReasonsOfTheFirstFailingRun(Model):
    """Gives the reasons of one run only."""

    def proposal_reasons(self, runs: list[str], case_id: str, pass_score: int) -> list[str]:
        for run in runs:
            if case_id in self.runs[run].cases:
                reasons = self.reasons_of(run, case_id, pass_score)
                if reasons:
                    return sorted(reasons)
        return []


class ProposalReasonsAreNotSorted(Model):
    """Lists the reasons of each run in turn, as found."""

    def proposal_reasons(self, runs: list[str], case_id: str, pass_score: int) -> list[str]:
        found: list[str] = []
        for run in runs:
            if case_id in self.runs[run].cases:
                for reason in self.reasons_of(run, case_id, pass_score):
                    if reason not in found:
                        found.append(reason)
        return found


class ProposalReasonsRepeat(Model):
    """Repeats a reason that several runs share."""

    def proposal_reasons(self, runs: list[str], case_id: str, pass_score: int) -> list[str]:
        found: list[str] = []
        for run in runs:
            if case_id in self.runs[run].cases:
                found.extend(self.reasons_of(run, case_id, pass_score))
        return sorted(found)


class EveryNewCaseIsProposed(Model):
    """Proposes a new case also when it passes."""

    def needs_proposal(self, reasons: list[str]) -> bool:
        return True


class ProposalsOfLowScoresUseTheJudge(Model):
    """Judges a new case by the judge's score even when a human gave one."""

    def verdict_score(self, table: Run, case_id: str, criterion: str) -> int:
        return table.judge[case_id][criterion]


class DefaultThresholdAllowsADrop(Model):
    """Starts with a drop of 100 hundredths allowed."""

    def __init__(self) -> None:
        super().__init__()
        self.max_drop = 100


class CriticalCasesAreAppended(Model):
    """Adds the critical cases to the earlier ones."""

    def set_gate(self, critical: list[str], max_drop: int) -> None:
        self.critical = self.critical + list(critical)
        self.max_drop = max_drop


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor and the setters."""
    model = model_type()
    results: list[Any] = [None]
    for op, arguments in zip(case["ops"][1:], case["args"][1:], strict=True):
        results.append(getattr(model, snake_case(op))(*arguments))
    return results


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError, StopIteration):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_a_hidden_case_has_a_kappa_that_is_undefined_and_one_that_is_rounded_from_a_half():
    kappas = [
        row[3]
        for case in HIDDEN_CASES
        for op, result in zip(case["ops"], case["expected"], strict=True)
        if op == "agreement"
        for row in result
    ]
    assert "undefined" in kappas
    assert "63" in kappas
    assert "-313" in kappas
    assert "0" in kappas


def test_a_hidden_case_blocks_and_ships_with_a_proposal_at_the_same_time_as_a_plain_ship():
    decisions = [
        (result[0][1], any(row[0] == "propose" for row in result))
        for case in HIDDEN_CASES
        for op, result in zip(case["ops"], case["expected"], strict=True)
        if op == "gate"
    ]
    assert ("ship", False) in decisions
    assert ("ship", True) in decisions
    assert ("block", True) in decisions
    assert ("block", False) in decisions
