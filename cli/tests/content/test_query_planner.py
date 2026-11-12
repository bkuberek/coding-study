"""query-planner promises that its hidden cases catch the classic mistakes of a first query
planner: a parser or a checker that accepts too much or reports the wrong error, filters left above
the joins, estimates rounded the wrong way or built from the estimates of other joins, a join order
found greedily or with the wrong cost or tie rule, and access paths and join methods costed wrongly.
These tests replay every case against a model of the planner written from the statement, which
must give every expected output, and against that model with one mistake planted at a time, which
some hidden case must fail. The model tries every join order instead of the reference's dynamic
programming over subsets. A mistake that crashes fails its case, as a thrown exception does in the
grader."""

import itertools
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0382-query-planner"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

KEYWORDS = ("SELECT", "FROM", "JOIN", "ON", "WHERE", "AND")
TOKEN = re.compile(r" *(?:([A-Za-z_][A-Za-z0-9_]*)|(-?[0-9]+)|([*,.=<>]))")

Column = tuple[str, str]
Condition = tuple[Column, str, str]


class RejectedError(Exception):
    """A query that fails a check; the message is the error line without `error: `."""


class Query:
    """The pieces of a checked query: tables in written order, selected columns or None for `*`,
    join conditions as (new table, earlier column, new column), and the WHERE conditions."""

    def __init__(self) -> None:
        self.tables: list[str] = []
        self.selected: list[Column] | None = None
        self.edges: list[tuple[str, Column, Column]] = []
        self.where: list[Condition] = []


class Model:
    """The planner as the statement words it, one method per rule; each mistake overrides one."""

    def __init__(self) -> None:
        self.catalog: dict[str, list[str]] = {}
        self.stats: dict[str, tuple[int, list[int]]] = {}
        self.indexed: set[Column] = set()

    # --- level 1: tokens, grammar and checks
    def tokens(self, sql: str) -> list[str]:
        found, at = [], 0
        while sql[at:].strip(" "):
            match = TOKEN.match(sql, at)
            if not match:
                raise RejectedError("syntax")
            found.append(match.group(match.lastindex or 0))
            at = match.end()
        return found

    def is_name(self, token: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token)) and token not in KEYWORDS

    def grammar(self, sql: str) -> tuple[list[Column] | None, list[str], list, list[Condition]]:
        words = [*self.tokens(sql), "<end>"]
        at = 0

        def take(expected: str | None = None) -> str:
            nonlocal at
            token = words[at]
            if expected is not None and token != expected:
                raise RejectedError("syntax")
            at += 1
            return token

        def name() -> str:
            if not self.is_name(words[at]):
                raise RejectedError("syntax")
            return take()

        def column() -> Column:
            table = name()
            take(".")
            return table, name()

        take("SELECT")
        selected = None
        if words[at] == "*":
            take()
        else:
            selected = [column()]
            while words[at] == ",":
                take()
                selected.append(column())
        take("FROM")
        tables = [name()]
        joins = []
        while words[at] == "JOIN":
            take()
            tables.append(name())
            take("ON")
            left = column()
            take("=")
            joins.append((tables[-1], left, column()))
        where: list[Condition] = []
        if words[at] == "WHERE":
            take()
            while True:
                col = column()
                op = take()
                if op not in "=<>" or not re.fullmatch(r"-?[0-9]+", words[at]):
                    raise RejectedError("syntax")
                where.append((col, op, take()))
                if words[at] != "AND":
                    break
                take()
        take("<end>")
        return selected, tables, joins, where

    def check(self, sql: str) -> Query:
        selected, tables, joins, where = self.grammar(sql)
        query = Query()
        for table in tables:
            if table not in self.catalog:
                raise RejectedError(f"unknown-table {table}")
            if self.repeated(query, table):
                raise RejectedError(f"duplicate-table {table}")
            query.tables.append(table)
        written = list(selected or []) + [c for _, a, b in joins for c in (a, b)]
        for table, col in written + [cond[0] for cond in where]:
            if not self.column_known(query, table, col):
                raise RejectedError(f"unknown-column {table}.{col}")
        for table, first, second in joins:
            before = self.before(query, table)
            if second[0] == table and first[0] in before:
                query.edges.append((table, first, second))
            elif first[0] == table and second[0] in before:
                query.edges.append((table, second, first))
            else:
                raise RejectedError(f"bad-join {table}")
        query.selected = selected
        query.where = self.pushed(where, query)
        return query

    def pushed(self, where: list[Condition], query: Query) -> list[Condition]:
        return where

    def repeated(self, query: Query, table: str) -> bool:
        return table in query.tables

    def column_known(self, query: Query, table: str, col: str) -> bool:
        return table in query.tables and col in self.catalog[table]

    def before(self, query: Query, table: str) -> list[str]:
        return query.tables[: query.tables.index(table)]

    def conditions_of(self, query: Query, table: str) -> list[Condition]:
        return [cond for cond in query.where if cond[0][0] == table]

    def text(self, cond: Condition) -> str:
        return f"{cond[0][0]}.{cond[0][1]} {cond[1]} {cond[2]}"

    def join_text(self, earlier: Column, new: Column) -> str:
        return f"{earlier[0]}.{earlier[1]} = {new[0]}.{new[1]}"

    def head(self, query: Query) -> str:
        if query.selected is None:
            return "project *"
        return "project " + ", ".join(f"{t}.{c}" for t, c in query.selected)

    # --- level 2: estimates
    def nearest(self, numerator: int, denominator: int) -> int:
        quotient, remainder = divmod(numerator, denominator)
        return max(1, quotient + (2 * remainder >= denominator))

    def distinct(self, col: Column) -> int:
        return self.stats[col[0]][1][self.catalog[col[0]].index(col[1])]

    def divisor(self, cond: Condition) -> int:
        return self.distinct(cond[0]) if cond[1] == "=" else 3

    def filtered(self, query: Query, table: str) -> int:
        rows = self.stats[table][0]
        conditions = self.conditions_of(query, table)
        if not conditions:
            return rows
        product = 1
        for cond in conditions:
            product *= self.divisor(cond)
        return self.nearest(rows, product)

    def edge_divisor(self, earlier: Column, new: Column) -> int:
        return max(self.distinct(earlier), self.distinct(new))

    def set_rows(self, query: Query, tables: Sequence[str]) -> int:
        top = 1
        for table in tables:
            top *= self.filtered(query, table)
        bottom = 1
        for table, earlier, new in query.edges:
            if table in tables and earlier[0] in tables:
                bottom *= self.edge_divisor(earlier, new)
        return self.nearest(top, bottom)

    def require_stats(self, query: Query) -> None:
        for table in query.tables:
            if table not in self.stats:
                raise RejectedError(f"no-stats {table}")

    # --- join orders
    def link(self, query: Query, done: Sequence[str], table: str) -> tuple[Column, Column] | None:
        for new_table, earlier, new in query.edges:
            if new_table == table and earlier[0] in done:
                return earlier, new
            if earlier[0] == table and new_table in done:
                return new, earlier
        return None

    def orders(self, query: Query) -> list[list[str]]:
        valid = []
        for order in itertools.permutations(query.tables):
            if all(self.link(query, order[:k], order[k]) for k in range(1, len(order))):
                valid.append(list(order))
        return valid

    def start_cost(self, query: Query, table: str, level: int) -> int:
        return self.access(query, table)[0] if level == 4 else 0

    def step_cost(self, query: Query, done: Sequence[str], table: str, level: int) -> int:
        if level == 3:
            return self.set_rows(query, [*done, table])
        return self.method(query, done, table)[1]

    def total(self, query: Query, order: list[str], level: int) -> int:
        cost = self.start_cost(query, order[0], level)
        for k in range(1, len(order)):
            cost += self.step_cost(query, order[:k], order[k], level)
        return cost

    def chosen(self, query: Query, level: int) -> list[str]:
        return min(self.orders(query), key=lambda order: (self.total(query, order, level), order))

    # --- level 4: access paths and methods
    def index_reads(self, query: Query, table: str, cond: Condition) -> int:
        return self.nearest(self.stats[table][0], self.distinct(cond[0]))

    def usable(self, cond: Condition) -> bool:
        return cond[1] == "=" and cond[0] in self.indexed

    def access(self, query: Query, table: str) -> tuple[int, Condition | None]:
        options: list[tuple[int, int, Condition | None]] = [(self.stats[table][0], -1, None)]
        for position, cond in enumerate(self.conditions_of(query, table)):
            if self.usable(cond):
                options.append((4 * self.index_reads(query, table, cond), position, cond))
        cost, _, cond = min(options, key=lambda option: (option[0], option[1]))
        return cost, cond

    def method(self, query: Query, done: Sequence[str], table: str) -> tuple[str, int]:
        left = self.set_rows(query, done)
        reads = self.access(query, table)[0]
        nested = left * reads
        hashed = reads + self.filtered(query, table) + left
        return ("nested loop", nested) if nested <= hashed else ("hash join", hashed)

    # --- printing
    def leaf(self, query: Query, table: str, level: int) -> list[str]:
        conditions = self.conditions_of(query, table)
        if level == 1:
            bottom = f"scan {table}"
        elif level < 4:
            bottom = f"scan {table} (rows={self.stats[table][0]})"
        else:
            cost, used = self.access(query, table)
            if used is None:
                bottom = f"full scan {table} (rows={self.stats[table][0]} cost={cost})"
            else:
                reads = self.index_reads(query, table, used)
                bottom = f"index scan {self.text(used)} (rows={reads} cost={cost})"
                conditions = list(conditions)
                conditions.remove(used)
        if not conditions:
            return [bottom]
        top = "filter " + " AND ".join(self.text(cond) for cond in conditions)
        if level > 1:
            top += f" (rows={self.filtered(query, table)})"
        return [top, "  " + bottom]

    def tree(self, query: Query, order: list[str], level: int) -> list[str]:
        """Prints the left-deep plan by building it bottom up as indented blocks."""
        block = self.leaf(query, order[0], level)
        cost = self.start_cost(query, order[0], level)
        for k in range(1, len(order)):
            link = self.link(query, order[:k], order[k])
            assert link is not None
            earlier, new = link
            rows = self.set_rows(query, order[: k + 1]) if level > 1 else 0
            word = self.method(query, order[:k], order[k])[0] if level == 4 else "join"
            if level > 2:
                cost += self.step_cost(query, order[:k], order[k], level)
            line = f"{word} {self.join_text(earlier, new)}"
            if level == 2:
                line += f" (rows={rows})"
            if level > 2:
                line += f" (rows={rows} cost={cost})"
            right = self.leaf(query, order[k], level)
            block = [line] + ["  " + text for text in block + right]
        return [self.head(query)] + ["  " + text for text in block]

    def plan(self, sql: str, level: int) -> list[str]:
        try:
            query = self.check(sql)
            if level > 1:
                self.require_stats(query)
            order = query.tables if level < 3 else self.chosen(query, level)
            return self.tree(query, order, level)
        except RejectedError as error:
            return [f"error: {error}"]

    # --- the API
    def add_table(self, table: str, columns: list[str]) -> str:
        if table in self.catalog:
            return "duplicate"
        self.catalog[table] = columns
        return "ok"

    def logical_plan(self, sql: str) -> list[str]:
        return self.plan(sql, 1)

    def stats_ok(self, table: str, rows: int, distinct: list[int]) -> bool:
        return (
            len(distinct) == len(self.catalog[table])
            and min([rows, *distinct]) >= 1
            and (max(distinct) <= rows)
        )

    def analyze(self, table: str, rows: int, distinct: list[int]) -> str:
        if table not in self.catalog:
            return "unknown-table"
        if not self.stats_ok(table, rows, distinct):
            return "bad-stats"
        self.stats[table] = (rows, distinct)
        return "ok"

    def estimate(self, sql: str) -> list[str]:
        return self.plan(sql, 2)

    def optimize(self, sql: str) -> list[str]:
        return self.plan(sql, 3)

    def add_index(self, table: str, column: str) -> str:
        if table not in self.catalog:
            return "unknown-table"
        if column not in self.catalog[table]:
            return "unknown-column"
        if (table, column) in self.indexed:
            return "duplicate"
        self.indexed.add((table, column))
        return "ok"

    def explain(self, sql: str) -> list[str]:
        return self.plan(sql, 4)


# ------------------------------------------------------------------ level 1 mistakes
class KeywordsInAnyCase(Model):
    """Accepts `select` and `from` in small letters."""

    def tokens(self, sql: str) -> list[str]:
        found = super().tokens(sql)
        return [token.upper() if token.upper() in KEYWORDS else token for token in found]


class AcceptsComparisonOfTwoColumns(Model):
    """Lets a WHERE condition compare two columns, read as a comparison with 0."""

    def grammar(self, sql: str) -> tuple[list[Column] | None, list[str], list, list[Condition]]:
        if "WHERE" in sql:
            head, tail = sql.split("WHERE", 1)
            sql = head + "WHERE" + re.sub(r"(\w+\.\w+) (.) \w+\.\w+", r"\1 \2 0", tail)
        return super().grammar(sql)


class SpaceInsideANumberIsFine(Model):
    """Reads `- 3` as the number -3."""

    def tokens(self, sql: str) -> list[str]:
        return super().tokens(re.sub(r"- +([0-9])", r"-\1", sql))


class ColumnsCheckedAgainstTheCatalog(Model):
    """Accepts a column of a table that is in the catalog but not in the query."""

    def column_known(self, query: Query, table: str, col: str) -> bool:
        return table in self.catalog and col in self.catalog[table]


class ColumnsBeforeTables(Model):
    """Checks the columns before the tables."""

    def check(self, sql: str) -> Query:
        selected, _tables, _joins, where = self.grammar(sql)
        for table, col in list(selected or []) + [cond[0] for cond in where]:
            if table in self.catalog and col not in self.catalog[table]:
                raise RejectedError(f"unknown-column {table}.{col}")
        return super().check(sql)


class RepeatedTableAllowed(Model):
    """Lets a table appear twice."""

    def repeated(self, query: Query, table: str) -> bool:
        return False


class JoinToALaterTableAllowed(Model):
    """Accepts an ON condition that names any other table of the query."""

    def before(self, query: Query, table: str) -> list[str]:
        return [other for other in query.tables if other != table]


class FiltersAboveTheJoins(Model):
    """Leaves every WHERE condition on the first table's side, as if no condition were pushed."""

    def conditions_of(self, query: Query, table: str) -> list[Condition]:
        return list(query.where) if table == query.tables[0] else []


class ConditionsSorted(Model):
    """Sorts the conditions of a filter."""

    def conditions_of(self, query: Query, table: str) -> list[Condition]:
        return sorted(super().conditions_of(query, table))


class JoinWrittenAsGiven(Model):
    """Writes the new table's column first when the query does."""

    def join_text(self, earlier: Column, new: Column) -> str:
        return f"{new[0]}.{new[1]} = {earlier[0]}.{earlier[1]}"


class SelectedColumnsSorted(Model):
    """Sorts the selected columns."""

    def head(self, query: Query) -> str:
        if query.selected is None:
            return "project *"
        return "project " + ", ".join(f"{t}.{c}" for t, c in sorted(query.selected))


# ------------------------------------------------------------------ level 2 mistakes
class RoundsDown(Model):
    """Truncates instead of rounding."""

    def nearest(self, numerator: int, denominator: int) -> int:
        return max(1, numerator // denominator)


class RoundsHalfToEven(Model):
    """Uses banker's rounding, as Python's round does."""

    def nearest(self, numerator: int, denominator: int) -> int:
        return max(1, round(numerator / denominator))


class NoFloorOfOne(Model):
    """Lets an estimate be 0."""

    def nearest(self, numerator: int, denominator: int) -> int:
        quotient, remainder = divmod(numerator, denominator)
        return quotient + (2 * remainder >= denominator)


class JoinDividesBySmallerCount(Model):
    """Divides a join by the smaller distinct count."""

    def edge_divisor(self, earlier: Column, new: Column) -> int:
        return min(self.distinct(earlier), self.distinct(new))


class RangeKeepsHalf(Model):
    """Lets half the rows pass a `<` or `>` condition."""

    def divisor(self, cond: Condition) -> int:
        return self.distinct(cond[0]) if cond[1] == "=" else 2


class JoinOfUnfilteredTables(Model):
    """Multiplies the rows of the tables, ignoring their filters."""

    def set_rows(self, query: Query, tables: Sequence[str]) -> int:
        top = 1
        for table in tables:
            top *= self.stats[table][0]
        bottom = 1
        for table, earlier, new in query.edges:
            if table in tables and earlier[0] in tables:
                bottom *= self.edge_divisor(earlier, new)
        return self.nearest(top, bottom)


class JoinFromTheJoinBelow(Model):
    """Estimates a join from the rounded estimate of the join below it."""

    def set_rows(self, query: Query, tables: Sequence[str]) -> int:
        tables = list(tables)
        rows = self.filtered(query, tables[0])
        for k in range(1, len(tables)):
            link = self.link(query, tables[:k], tables[k])
            divisor = self.edge_divisor(*link) if link else 1
            rows = self.nearest(rows * self.filtered(query, tables[k]), divisor)
        return rows


class FilterDividesEachCondition(Model):
    """Rounds after each condition of a filter."""

    def filtered(self, query: Query, table: str) -> int:
        rows = self.stats[table][0]
        for cond in self.conditions_of(query, table):
            rows = self.nearest(rows, self.divisor(cond))
        return rows


class DistinctAboveRowsAccepted(Model):
    """Accepts a distinct count above the number of rows."""

    def stats_ok(self, table: str, rows: int, distinct: list[int]) -> bool:
        return len(distinct) == len(self.catalog[table]) and min([rows, *distinct]) >= 1


class StatsLengthUnchecked(Model):
    """Accepts a list of counts of the wrong length."""

    def stats_ok(self, table: str, rows: int, distinct: list[int]) -> bool:
        return min([rows, *distinct]) >= 1 and max(distinct) <= rows


class NoStatsIgnored(Model):
    """Treats a table without statistics as having one row."""

    def require_stats(self, query: Query) -> None:
        for table in query.tables:
            self.stats.setdefault(table, (1, [1] * len(self.catalog[table])))


# ------------------------------------------------------------------ level 3 mistakes
class CostCountsTheScans(Model):
    """Adds the rows of every table read to the cost."""

    def start_cost(self, query: Query, table: str, level: int) -> int:
        return self.stats[table][0] if level == 3 else super().start_cost(query, table, level)

    def step_cost(self, query: Query, done: Sequence[str], table: str, level: int) -> int:
        extra = self.stats[table][0] if level == 3 else 0
        return super().step_cost(query, done, table, level) + extra


class CostOfTheLastJoinOnly(Model):
    """Compares plans by the size of their result, which is the same for all of them."""

    def total(self, query: Query, order: list[str], level: int) -> int:
        return self.set_rows(query, order) if level == 3 else super().total(query, order, level)


class CostCountsTheLeftInputs(Model):
    """Counts the rows that enter each join from the left instead of the rows it produces."""

    def step_cost(self, query: Query, done: Sequence[str], table: str, level: int) -> int:
        if level == 3:
            return self.set_rows(query, done)
        return super().step_cost(query, done, table, level)


class TiesToTheLastName(Model):
    """Breaks ties toward the order whose names come last."""

    def chosen(self, query: Query, level: int) -> list[str]:
        candidates = self.orders(query)
        best = min(self.total(query, order, level) for order in candidates)
        return max(order for order in candidates if self.total(query, order, level) == best)


class TiesToTheWrittenOrder(Model):
    """Keeps the first cheapest order in the order the permutations come, from the written one."""

    def chosen(self, query: Query, level: int) -> list[str]:
        return min(self.orders(query), key=lambda order: self.total(query, order, level))


class CartesianProductsAllowed(Model):
    """Considers every order, even one that pairs tables without a condition."""

    def orders(self, query: Query) -> list[list[str]]:
        return [list(order) for order in itertools.permutations(query.tables)]

    def link(self, query: Query, done: Sequence[str], table: str) -> tuple[Column, Column] | None:
        found = super().link(query, done, table)
        return found if found else ((done[0], "*"), (table, "*"))


class GreedySmallestNext(Model):
    """Starts from the smallest table and always adds the join with the smallest result."""

    def chosen(self, query: Query, level: int) -> list[str]:
        order = [min(query.tables, key=lambda t: (self.filtered(query, t), t))]
        while len(order) < len(query.tables):
            options = [t for t in query.tables if t not in order and self.link(query, order, t)]
            order.append(min(options, key=lambda t: (self.set_rows(query, [*order, t]), t)))
        return order


# ------------------------------------------------------------------ level 4 mistakes
class IndexReadsCostOne(Model):
    """Counts a row read through an index like a row of a full scan."""

    def access(self, query: Query, table: str) -> tuple[int, Condition | None]:
        options: list[tuple[int, int, Condition | None]] = [(self.stats[table][0], -1, None)]
        for position, cond in enumerate(self.conditions_of(query, table)):
            if self.usable(cond):
                options.append((self.index_reads(query, table, cond), position, cond))
        cost, _, cond = min(options, key=lambda option: (option[0], option[1]))
        return cost, cond


class IndexForRangesToo(Model):
    """Uses an index for `<` and `>` as well."""

    def usable(self, cond: Condition) -> bool:
        return cond[0] in self.indexed


class IndexWheneverThereIsOne(Model):
    """Takes an index scan whenever an index serves a condition."""

    def access(self, query: Query, table: str) -> tuple[int, Condition | None]:
        for cond in self.conditions_of(query, table):
            if self.usable(cond):
                return 4 * self.index_reads(query, table, cond), cond
        return self.stats[table][0], None


class IndexTieGoesToTheIndex(Model):
    """Prefers the index when it costs the same as a full scan."""

    def access(self, query: Query, table: str) -> tuple[int, Condition | None]:
        cost, used = super().access(query, table)
        if used is None:
            for cond in self.conditions_of(query, table):
                if self.usable(cond) and 4 * self.index_reads(query, table, cond) == cost:
                    return cost, cond
        return cost, used


class HashJoinWithoutBuilding(Model):
    """Leaves the hash table's rows out of a hash join."""

    def method(self, query: Query, done: Sequence[str], table: str) -> tuple[str, int]:
        left = self.set_rows(query, done)
        reads = self.access(query, table)[0]
        nested, hashed = left * reads, reads + left
        return ("nested loop", nested) if nested <= hashed else ("hash join", hashed)


class NestedLoopTimesRows(Model):
    """Costs a nested loop by the right table's rows instead of its access cost."""

    def method(self, query: Query, done: Sequence[str], table: str) -> tuple[str, int]:
        left = self.set_rows(query, done)
        reads = self.access(query, table)[0]
        nested = left * self.stats[table][0]
        hashed = reads + self.filtered(query, table) + left
        return ("nested loop", nested) if nested <= hashed else ("hash join", hashed)


class MethodTieGoesToHash(Model):
    """Picks the hash join when both methods cost the same."""

    def method(self, query: Query, done: Sequence[str], table: str) -> tuple[str, int]:
        name, cost = super().method(query, done, table)
        left = self.set_rows(query, done)
        reads = self.access(query, table)[0]
        if left * reads == reads + self.filtered(query, table) + left:
            return "hash join", cost
        return name, cost


class FirstAccessNotCounted(Model):
    """Leaves the first table's access out of the plan's cost."""

    def start_cost(self, query: Query, table: str, level: int) -> int:
        return 0


class IndexFilterFromTheIndexRows(Model):
    """Estimates the filter above an index scan from the rows the index returns."""

    def filtered(self, query: Query, table: str) -> int:
        if table in self.stats and any(
            self.usable(cond) for cond in self.conditions_of(query, table)
        ):
            _cost, used = self.access(query, table)
            if used is not None:
                rows = self.index_reads(query, table, used)
                product = 1
                for cond in self.conditions_of(query, table):
                    if cond != used:
                        product *= self.divisor(cond)
                return self.nearest(rows, product)
        return super().filtered(query, table)


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (
        IndexError,
        KeyError,
        ValueError,
        TypeError,
        ZeroDivisionError,
        AssertionError,
        RejectedError,
    ):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_every_cost_and_estimate_fits_in_a_double():
    """The statement promises that every estimate and cost of the cases is below 2^53."""
    numbers = [
        int(value)
        for case in CASES
        for result in case["expected"]
        if isinstance(result, list)
        for line in result
        for value in re.findall(r"(?:rows|cost)=([0-9]+)", line)
    ]
    assert numbers
    assert max(numbers) < 2**53
