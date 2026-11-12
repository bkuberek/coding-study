KEYWORDS = {"SELECT", "FROM", "JOIN", "ON", "WHERE", "AND"}
SYMBOLS = set("*,.=<>")
RANDOM_READ = 4


class QueryError(Exception):
    pass


def tokenize(sql: str) -> list[str]:
    tokens = []
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == " ":
            i += 1
        elif char.isascii() and (char.isalpha() or char == "_"):
            j = i
            while j < len(sql) and sql[j].isascii() and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            tokens.append(sql[i:j])
            i = j
        elif char.isascii() and char.isdigit() or (char == "-" and sql[i + 1 : i + 2].isdigit()):
            j = i + 1
            while j < len(sql) and sql[j].isascii() and sql[j].isdigit():
                j += 1
            if j - i - (1 if char == "-" else 0) > 9:
                raise QueryError("syntax")
            tokens.append(sql[i:j])
            i = j
        elif char in SYMBOLS:
            tokens.append(char)
            i += 1
        else:
            raise QueryError("syntax")
    return tokens


class Query:
    """SELECT ... FROM t [JOIN u ON a.x = b.y]... [WHERE c op n [AND ...]], as written."""

    def __init__(self, sql: str) -> None:
        self.tokens = tokenize(sql)
        self.pos = 0
        self.expect("SELECT")
        self.columns: list[tuple[str, str]] | None = None
        if self.peek() == "*":
            self.pos += 1
        else:
            self.columns = [self.column()]
            while self.peek() == ",":
                self.pos += 1
                self.columns.append(self.column())
        self.expect("FROM")
        self.tables = [self.name()]
        self.joins: list[tuple[str, tuple[str, str], tuple[str, str]]] = []
        while self.peek() == "JOIN":
            self.pos += 1
            table = self.name()
            self.tables.append(table)
            self.expect("ON")
            left = self.column()
            self.expect("=")
            self.joins.append((table, left, self.column()))
        self.conditions: list[tuple[tuple[str, str], str, str]] = []
        if self.peek() == "WHERE":
            self.pos += 1
            self.conditions.append(self.condition())
            while self.peek() == "AND":
                self.pos += 1
                self.conditions.append(self.condition())
        if self.pos != len(self.tokens):
            raise QueryError("syntax")

    def peek(self) -> str:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ""

    def expect(self, token: str) -> None:
        if self.peek() != token:
            raise QueryError("syntax")
        self.pos += 1

    def name(self) -> str:
        token = self.peek()
        if not (token[:1].isalpha() or token[:1] == "_") or token in KEYWORDS:
            raise QueryError("syntax")
        self.pos += 1
        return token

    def column(self) -> tuple[str, str]:
        table = self.name()
        self.expect(".")
        return table, self.name()

    def condition(self) -> tuple[tuple[str, str], str, str]:
        column = self.column()
        op = self.peek()
        if op not in ("=", "<", ">"):
            raise QueryError("syntax")
        self.pos += 1
        value = self.peek()
        if not value or not (value[0].isdigit() or value[0] == "-"):
            raise QueryError("syntax")
        self.pos += 1
        return column, op, value

    def column_refs(self) -> list[tuple[str, str]]:
        refs = list(self.columns or [])
        for _, left, right in self.joins:
            refs += [left, right]
        return refs + [column for column, _, _ in self.conditions]


def dotted(column: tuple[str, str]) -> str:
    return f"{column[0]}.{column[1]}"


def show_condition(condition: tuple[tuple[str, str], str, str]) -> str:
    column, op, value = condition
    return f"{dotted(column)} {op} {value}"


def rounded(numerator: int, denominator: int) -> int:
    """numerator / denominator rounded half up, and at least 1."""
    return max(1, (2 * numerator + denominator) // (2 * denominator))


class Plan:
    """One checked query with everything the planner needs: the tables in written order, the
    conditions of each table, and the join edges, each written with the earlier table first."""

    def __init__(self, planner: "QueryPlanner", sql: str, need_stats: bool) -> None:
        query = Query(sql)
        seen: set[str] = set()
        for table in query.tables:
            if table not in planner.columns:
                raise QueryError(f"unknown-table {table}")
            if table in seen:
                raise QueryError(f"duplicate-table {table}")
            seen.add(table)
        for table, column in query.column_refs():
            if table not in seen or column not in planner.columns[table]:
                raise QueryError(f"unknown-column {table}.{column}")
        self.edges: list[tuple[str, str, tuple[str, str], tuple[str, str]]] = []
        for index, (table, left, right) in enumerate(query.joins):
            earlier = query.tables[: index + 1]
            if left[0] == table and right[0] in earlier:
                left, right = right, left
            elif not (right[0] == table and left[0] in earlier):
                raise QueryError(f"bad-join {table}")
            self.edges.append((left[0], table, left, right))
        if need_stats:
            for table in query.tables:
                if table not in planner.stats:
                    raise QueryError(f"no-stats {table}")
        self.planner = planner
        self.query = query
        self.tables = query.tables
        self.where = {t: [c for c in query.conditions if c[0][0] == t] for t in self.tables}

    def head(self) -> str:
        columns = self.query.columns
        return "project " + ("*" if columns is None else ", ".join(map(dotted, columns)))

    # --- estimates
    def distinct(self, column: tuple[str, str]) -> int:
        _, distinct = self.planner.stats[column[0]]
        return distinct[self.planner.columns[column[0]].index(column[1])]

    def divisor(self, condition: tuple[tuple[str, str], str, str]) -> int:
        return self.distinct(condition[0]) if condition[1] == "=" else 3

    def base(self, table: str) -> int:
        return self.planner.stats[table][0]

    def out(self, table: str) -> int:
        """The rows of the table after its conditions."""
        if not self.where[table]:
            return self.base(table)
        divisor = 1
        for condition in self.where[table]:
            divisor *= self.divisor(condition)
        return rounded(self.base(table), divisor)

    def edge_divisor(self, edge: tuple) -> int:
        return max(self.distinct(edge[2]), self.distinct(edge[3]))

    def rows(self, tables: frozenset[str]) -> int:
        numerator = 1
        for table in tables:
            numerator *= self.out(table)
        denominator = 1
        for edge in self.edges:
            if edge[0] in tables and edge[1] in tables:
                denominator *= self.edge_divisor(edge)
        return rounded(numerator, denominator)

    def edge_into(self, joined: frozenset[str], table: str) -> tuple | None:
        """The join edge between a table and a set it joins, written with the set's column first."""
        for left, right, left_column, right_column in self.edges:
            if right == table and left in joined:
                return left_column, right_column
            if left == table and right in joined:
                return right_column, left_column
        return None

    # --- level 4 access paths
    def access(self, table: str) -> tuple[int, int | None]:
        """The cheapest way to read a table: (cost, index of the condition an index serves, or
        None for a full scan). Ties keep the full scan, then the condition written first."""
        best = (self.base(table), None)
        indexed = self.planner.indexes.get(table, set())
        for position, condition in enumerate(self.where[table]):
            if condition[1] == "=" and condition[0][1] in indexed:
                cost = RANDOM_READ * rounded(self.base(table), self.distinct(condition[0]))
                if cost < best[0]:
                    best = (cost, position)
        return best

    # --- printing
    def table_lines(self, table: str, depth: int, mode: int) -> list[str]:
        """The lines that read one table: its scan, under a filter when conditions remain."""
        pad = "  " * depth
        conditions = self.where[table]
        if mode == 1:
            scan = f"scan {table}"
        elif mode in (2, 3):
            scan = f"scan {table} (rows={self.base(table)})"
        else:
            cost, used = self.access(table)
            if used is None:
                scan = f"full scan {table} (rows={self.base(table)} cost={cost})"
            else:
                matched = rounded(self.base(table), self.distinct(conditions[used][0]))
                scan = f"index scan {show_condition(conditions[used])} (rows={matched} cost={cost})"
                conditions = conditions[:used] + conditions[used + 1 :]
        if not conditions:
            return [pad + scan]
        shown = "filter " + " AND ".join(map(show_condition, conditions))
        if mode > 1:
            shown += f" (rows={self.out(table)})"
        return [pad + shown, pad + "  " + scan]

    def join_line(self, joined: frozenset[str], table: str, mode: int, cost: int) -> tuple[str, int]:
        """The line of the join that adds a table to the joined set, and the plan's cost after it."""
        left_column, right_column = self.edge_into(joined, table)
        name = "join"
        if mode == 4:
            name, step = self.join_step(self.rows(joined), table)
            cost += step
        elif mode == 3:
            cost += self.rows(joined | {table})
        text = f"{name} {dotted(left_column)} = {dotted(right_column)}"
        if mode == 2:
            text += f" (rows={self.rows(joined | {table})})"
        elif mode > 2:
            text += f" (rows={self.rows(joined | {table})} cost={cost})"
        return text, cost

    def lines(self, order: list[str], mode: int) -> list[str]:
        """The plan joining the tables in this order, left-deep, under its project line. Mode 1
        prints no numbers, 2 the rows, 3 the rows and the cost, 4 the access paths and the join
        methods."""
        depth = len(order)
        steps: list[str] = []
        joined = frozenset([order[0]])
        cost = self.access(order[0])[0] if mode == 4 else 0
        for table in order[1:]:
            text, cost = self.join_line(joined, table, mode, cost)
            joined = joined | {table}
            steps.append(text)
        # Pre-order: the last join on top, each join's left input below it, then the first
        # table; the table joined at step k is the right input of that join, at depth n - k + 1.
        result = [self.head()]
        for level, text in enumerate(reversed(steps)):
            result.append("  " * (level + 1) + text)
        result += self.table_lines(order[0], depth, mode)
        for k, table in enumerate(order[1:], start=1):
            result += self.table_lines(table, depth - k + 1, mode)
        return result

    def join_step(self, left_rows: int, table: str) -> tuple[str, int]:
        inner_cost = self.access(table)[0]
        nested = left_rows * inner_cost
        hashed = inner_cost + self.out(table) + left_rows
        return ("nested loop", nested) if nested <= hashed else ("hash join", hashed)

    # --- level 3 and 4: the best left-deep order
    def best_order(self, mode: int) -> list[str]:
        """Dynamic programming over subsets: the cheapest left-deep order of every connected set,
        built from the cheapest order of the set without its last table. Ties go to the order
        whose list of table names comes first."""
        best: dict[frozenset[str], tuple[int, list[str]]] = {}
        for table in self.tables:
            best[frozenset([table])] = (self.access(table)[0] if mode == 4 else 0, [table])
        for size in range(2, len(self.tables) + 1):
            for subset, (cost, order) in list(best.items()):
                if len(subset) != size - 1:
                    continue
                for table in self.tables:
                    if table in subset or self.edge_into(subset, table) is None:
                        continue
                    grown = subset | {table}
                    if mode == 4:
                        step = self.join_step(self.rows(subset), table)[1]
                    else:
                        step = self.rows(grown)
                    candidate = (cost + step, order + [table])
                    if grown not in best or candidate < best[grown]:
                        best[grown] = candidate
        return best[frozenset(self.tables)][1]


class QueryPlanner:
    """Parses a small SQL subset, checks it against the catalog, and plans it: written order with
    filters pushed to the scans, row estimates from table statistics, the cheapest left-deep join
    order by dynamic programming over subsets, then access paths and join methods."""

    def __init__(self) -> None:
        self.columns: dict[str, list[str]] = {}
        self.stats: dict[str, tuple[int, list[int]]] = {}
        self.indexes: dict[str, set[str]] = {}

    def _plan(self, sql: str, need_stats: bool, mode: int) -> list[str]:
        try:
            plan = Plan(self, sql, need_stats)
        except QueryError as error:
            return [f"error: {error}"]
        order = plan.best_order(mode) if mode >= 3 else plan.tables
        return plan.lines(order, mode)

    # Level 1
    def add_table(self, table: str, columns: list[str]) -> str:
        if table in self.columns:
            return "duplicate"
        self.columns[table] = list(columns)
        return "ok"

    def logical_plan(self, sql: str) -> list[str]:
        return self._plan(sql, False, 1)

    # Level 2
    def analyze(self, table: str, rows: int, distinct: list[int]) -> str:
        if table not in self.columns:
            return "unknown-table"
        if (
            len(distinct) != len(self.columns[table])
            or rows < 1
            or any(count < 1 or count > rows for count in distinct)
        ):
            return "bad-stats"
        self.stats[table] = (rows, list(distinct))
        return "ok"

    def estimate(self, sql: str) -> list[str]:
        return self._plan(sql, True, 2)

    # Level 3
    def optimize(self, sql: str) -> list[str]:
        return self._plan(sql, True, 3)

    # Level 4
    def add_index(self, table: str, column: str) -> str:
        if table not in self.columns:
            return "unknown-table"
        if column not in self.columns[table]:
            return "unknown-column"
        if column in self.indexes.setdefault(table, set()):
            return "duplicate"
        self.indexes[table].add(column)
        return "ok"

    def explain(self, sql: str) -> list[str]:
        return self._plan(sql, True, 4)
