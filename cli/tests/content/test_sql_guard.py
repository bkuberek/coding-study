"""sql-guard promises that its hidden cases catch the classic mistakes of checking SQL that a model
wrote: a scanner that ends a string at a doubled quote, nests comments or reads keywords by case, a
statement count that counts empty statements, a read-only rule that searches the raw text or the
inside of strings and comments, names compared with case, an alias visible where it should not be,
a table that hides its columns, a limit put after a comment or an offset, and a parameter check that
reports the wrong literals. These tests replay every case against a model of the guard written from
the statement, which must give every expected output, and against that model with one mistake
planted at a time, which some hidden case must fail. A mistake that crashes fails its case, as a
thrown exception does in the grader. The model reads the text with regular expressions and parses
it with binding powers, a different route from the reference solutions."""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, ClassVar, NamedTuple

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0328-sql-guard"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

QUERY_WORDS = frozenset(
    re.findall(
        r"\S+",
        "SELECT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET AS JOIN INNER LEFT RIGHT FULL OUTER "
        "CROSS ON AND OR NOT NULL IS IN LIKE BETWEEN DISTINCT ASC DESC UNION ALL TRUE FALSE "
        "WITH",
    )
)
FORBIDDEN_WORDS = frozenset(
    re.findall(
        r"\S+",
        "INSERT UPDATE DELETE MERGE REPLACE DROP CREATE ALTER TRUNCATE RENAME GRANT REVOKE CALL "
        "EXEC EXECUTE COPY ATTACH DETACH PRAGMA VACUUM SET INTO",
    )
)
NAIVE_LIST = ("insert", "update", "delete", "drop", "alter", "create", "truncate")
AGGREGATES = frozenset({"count", "sum", "avg", "min", "max"})
PREDICATE_BP = 40
Row = list[str]
Node = tuple[Any, ...]


class Tok(NamedTuple):
    kind: str
    text: str
    start: int
    end: int


class LexError(Exception):
    """A lexical error, carrying its code."""


class SyntaxProblemError(Exception):
    """A text outside the grammar, carrying the text of the token that does not fit."""


class Query(NamedTuple):
    items: list[tuple[Node | None, str | None]]
    sources: list[tuple[str, str]]
    conditions: list[Node]
    where: Node | None
    group: list[Node]
    having: Node | None
    order: list[Node]


class Model:
    """The guard as the statement words it. The scanner is a list of regular expressions tried in
    order, the parser climbs binding powers and builds a tree, and the rules read tokens and the
    tree. Each mistake below overrides one hook."""

    LINE = re.compile(r"--[^\n\r]*")
    STRING = re.compile(r"'(?:[^']|'')*+'")
    QUOTED = re.compile(r'"(?:[^"]|"")*+"')
    NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?|\.[0-9]+")
    SYMBOL = re.compile(r"<=|>=|<>|!=|\|\||[(),.*+\-/%=<>]")
    PLACEHOLDER = re.compile(r"\?|\$[0-9]+|:[A-Za-z_][A-Za-z0-9_]*")
    WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    FORBIDDEN = FORBIDDEN_WORDS
    NAIVE = NAIVE_LIST

    def __init__(self) -> None:
        self.allowed: dict[str, set[str]] = {}

    # ------------------------------------------------------------------ the scanner
    def block_comment_end(self, sql: str, pos: int) -> int:
        """The index after the `*/` that closes the comment at `pos`, or -1."""
        found = sql.find("*/", pos + 2)
        return -1 if found < 0 else found + 2

    def decode_string(self, raw: str) -> str:
        return raw[1:-1].replace("''", "'")

    def decode_name(self, raw: str) -> str:
        return raw[1:-1].replace('""', '"')

    def read_string(self, sql: str, pos: int) -> tuple[str, int]:
        found = self.STRING.match(sql, pos)
        if found is None:
            raise LexError("unterminated-string")
        return self.decode_string(found.group()), found.end()

    def word_token(self, word: str, start: int, end: int) -> Tok:
        if word.upper() in QUERY_WORDS | self.FORBIDDEN:
            return Tok("keyword", word.upper(), start, end)
        return Tok("identifier", word, start, end)

    def number_may_continue(self, sql: str, end: int) -> bool:
        return end < len(sql) and (sql[end].isalnum() or sql[end] == "_") and sql[end].isascii()

    def prefix_forbidden(self, word: str, sql: str, end: int) -> bool:
        return len(word) == 1 and word in "ENXBenxb" and sql[end : end + 1] == "'"

    def scan(self, sql: str) -> tuple[list[Tok], str]:
        tokens: list[Tok] = []
        pos = 0
        try:
            while pos < len(sql):
                token, pos = self.scan_one(sql, pos)
                if token is not None:
                    tokens.append(token)
        except LexError as problem:
            return tokens, str(problem)
        return tokens, ""

    def scan_one(self, sql: str, pos: int) -> tuple[Tok | None, int]:
        char = sql[pos]
        if char in " \t\n\r":
            return None, pos + 1
        line = self.LINE.match(sql, pos)
        if line:
            return Tok("comment", line.group(), pos, line.end()), line.end()
        if sql.startswith("/*", pos):
            end = self.block_comment_end(sql, pos)
            if end < 0:
                raise LexError("unterminated-comment")
            return Tok("comment", sql[pos:end], pos, end), end
        if char == "'":
            text, end = self.read_string(sql, pos)
            return Tok("string", text, pos, end), end
        if char == '"':
            return self.read_quoted(sql, pos)
        number = self.NUMBER.match(sql, pos)
        if number:
            if self.number_may_continue(sql, number.end()):
                raise LexError("malformed-number")
            return Tok("number", number.group(), pos, number.end()), number.end()
        word = self.WORD.match(sql, pos)
        if word:
            if self.prefix_forbidden(word.group(), sql, word.end()):
                raise LexError("prefixed-string")
            return self.word_token(word.group(), pos, word.end()), word.end()
        if char == ";":
            return Tok("semicolon", ";", pos, pos + 1), pos + 1
        placeholder = self.PLACEHOLDER.match(sql, pos)
        if placeholder:
            return Tok(
                "placeholder", placeholder.group(), pos, placeholder.end()
            ), placeholder.end()
        symbol = self.SYMBOL.match(sql, pos)
        if symbol:
            return Tok("symbol", symbol.group(), pos, symbol.end()), symbol.end()
        raise LexError("unexpected-character")

    def read_quoted(self, sql: str, pos: int) -> tuple[Tok, int]:
        found = self.QUOTED.match(sql, pos)
        if found is None:
            raise LexError("unterminated-identifier")
        if found.group() == '""':
            raise LexError("empty-identifier")
        return Tok("identifier", self.decode_name(found.group()), pos, found.end()), found.end()

    # ------------------------------------------------------------------ level 1
    def tokenize(self, sql: str) -> list[Row]:
        tokens, error = self.scan(sql)
        rows = [[t.kind, t.text] for t in self.listed(tokens)]
        if error:
            rows.append(["error", error])
        return rows

    def listed(self, tokens: list[Tok]) -> list[Tok]:
        return tokens

    def statements(self, tokens: list[Tok]) -> list[list[Tok]]:
        groups: list[list[Tok]] = [[]]
        for token in tokens:
            if token.kind == "semicolon":
                groups.append([])
            elif token.kind != "comment":
                groups[-1].append(token)
        return [group for group in groups if group]

    def statement_count(self, sql: str, tokens: list[Tok]) -> int:
        return len(self.statements(tokens))

    def check(self, sql: str) -> list[Row]:
        tokens, error = self.scan(sql)
        if error and self.lex_errors_count():
            return [["lex-error", error]]
        count = self.statement_count(sql, tokens)
        if count == 0:
            return self.when_empty()
        return [["multiple-statements", str(count)]] if count > 1 else []

    def lex_errors_count(self) -> bool:
        return True

    def when_empty(self) -> list[Row]:
        return [["empty", ""]]

    # ------------------------------------------------------------------ level 2
    def dedupe(self, rows: list[Row]) -> list[Row]:
        kept: list[Row] = []
        for row in rows:
            if row not in kept:
                kept.append(row)
        return kept

    def first_is_select(self, sql: str, first: Tok) -> bool:
        return first.kind == "keyword" and first.text == "SELECT"

    def not_select_rows(self, sql: str, groups: list[list[Tok]]) -> list[Row]:
        return [
            ["not-select", group[0].text]
            for group in groups
            if not self.first_is_select(sql, group[0])
        ]

    def forbidden_rows(self, tokens: list[Tok]) -> list[Row]:
        return [
            ["forbidden-keyword", t.text]
            for t in tokens
            if t.kind == "keyword" and t.text in self.FORBIDDEN
        ]

    def is_executable(self, comment: str) -> bool:
        return comment.startswith("/*!")

    def executable_rows(self, sql: str, tokens: list[Tok]) -> list[Row]:
        if any(t.kind == "comment" and self.is_executable(t.text) for t in tokens):
            return [["executable-comment", ""]]
        return []

    def read_only_tail(self, sql: str, tokens: list[Tok]) -> list[Row]:
        return [
            *self.not_select_rows(sql, self.statements(tokens)),
            *self.forbidden_rows(tokens),
            *self.executable_rows(sql, tokens),
        ]

    def check_read_only(self, sql: str) -> list[Row]:
        rows = self.check(sql)
        if rows and rows[0][0] in ("lex-error", "empty"):
            return rows
        tokens, _ = self.scan(sql)
        return self.dedupe(rows + self.read_only_tail(sql, tokens))

    def naive_check(self, sql: str) -> str:
        text = sql.lower()
        return "reject" if any(word in text for word in self.NAIVE) else "allow"

    def contrast(self, sql: str) -> str:
        naive = self.naive_check(sql)
        guard = "reject" if self.check_read_only(sql) else "allow"
        if naive == guard:
            return "agree"
        return "false-alarm" if naive == "reject" else "miss"

    # ------------------------------------------------------------------ level 3: the parser
    def parse(self, tokens: list[Tok]) -> Query:
        return _Parser(self, tokens).query()

    def allow_table(self, table: str, columns: list[str]) -> bool:
        key = self.fold(table)
        if key in self.allowed:
            return False
        self.allowed[key] = {self.fold(column) for column in columns}
        return True

    def fold(self, name: str) -> str:
        return name.lower()

    def allowed_columns(self, table: str) -> set[str] | None:
        return self.allowed.get(table)

    def events(self, query: Query) -> list[Node]:
        """The wildcards, calls and columns of the query in the order of their tokens."""
        aliases = {alias for _, alias in query.items if alias}
        found: list[Node] = []
        for item, _ in query.items:
            found.extend(self.walk(item) if item is not None else [("wildcard",)])
        for condition in query.conditions:
            found.extend(self.walk(condition))
        found.extend(self.walk(query.where))
        for node in query.group:
            found.extend(self.walk(node))
        found.extend(self.walk(query.having))
        found.extend(self.order_events(query.order, aliases))
        return found

    def order_events(self, order: list[Node], aliases: set[str]) -> list[Node]:
        return [
            e for node in order if not self.names_an_output(node, aliases) for e in self.walk(node)
        ]

    def names_an_output(self, node: Node, aliases: set[str]) -> bool:
        return node[0] == "col" and node[1] is None and node[2] in aliases

    def walk(self, node: Node | None) -> list[Node]:
        if node is None:
            return []
        kind = node[0]
        if kind == "col":
            return [node]
        if kind == "call":
            return [("function", node[1]), *[e for arg in node[2] for e in self.walk(arg)]]
        if kind in ("lit", "ph", "const"):
            return []
        return [e for child in node[1:] if isinstance(child, tuple) for e in self.walk(child)] + [
            e
            for child in node[1:]
            if isinstance(child, list)
            for part in child
            if isinstance(part, tuple)
            for e in self.walk(part)
        ]

    def source_rows(self, sources: list[tuple[str, str]]) -> list[Row]:
        rows: list[Row] = []
        used: list[str] = []
        for name, table in sources:
            if table not in self.allowed:
                rows.append(["table-not-allowed", table])
            if self.duplicate_of(name, used):
                rows.append(["duplicate-source", name])
            used.append(name)
        return rows

    def duplicate_of(self, name: str, used: list[str]) -> bool:
        return name in used

    def event_rows(self, event: Node, sources: list[tuple[str, str]]) -> list[Row]:
        if event[0] == "wildcard":
            return self.wildcard_rows()
        if event[0] == "function":
            return self.function_rows(event[1])
        _, qualifier, name = event
        if qualifier is not None:
            return self.qualified_rows(qualifier, name, sources)
        return self.unqualified_rows(name, sources)

    def wildcard_rows(self) -> list[Row]:
        return [["wildcard-not-allowed", "*"]]

    def function_rows(self, name: str) -> list[Row]:
        return [] if name in AGGREGATES else [["function-not-allowed", name]]

    def model_strict(self, name: str) -> bool:
        return name in AGGREGATES

    def source_table(self, qualifier: str, sources: list[tuple[str, str]]) -> str | None:
        for name, table in sources:
            if name == qualifier:
                return table
        return None

    def qualified_rows(
        self, qualifier: str, name: str, sources: list[tuple[str, str]]
    ) -> list[Row]:
        table = self.source_table(qualifier, sources)
        if table is None:
            return [["unknown-source", qualifier]]
        columns = self.allowed_columns(table)
        if columns is not None and name not in columns:
            return [["column-not-allowed", self.qualified_detail(qualifier, name)]]
        return []

    def qualified_detail(self, qualifier: str, name: str) -> str:
        return f"{qualifier}.{name}"

    def holders(self, name: str, sources: list[tuple[str, str]]) -> int:
        return sum(1 for _, table in sources if name in (self.allowed_columns(table) or set()))

    def unknown_may_hide(self, sources: list[tuple[str, str]]) -> bool:
        return any(table not in self.allowed for _, table in sources)

    def unqualified_rows(self, name: str, sources: list[tuple[str, str]]) -> list[Row]:
        count = self.holders(name, sources)
        if count > 1 and self.reports_ambiguity():
            return [["ambiguous-column", name]]
        if count == 0 and not self.unknown_may_hide(sources):
            return [["column-not-allowed", name]]
        return []

    def reports_ambiguity(self) -> bool:
        return True

    def access_rows(self, query: Query) -> list[Row]:
        tables = self.source_rows(query.sources)
        others = [row for e in self.events(query) for row in self.event_rows(e, query.sources)]
        return self.arrange(tables, others)

    def arrange(self, tables: list[Row], others: list[Row]) -> list[Row]:
        return self.dedupe(tables + others)

    def read_only_gate(self, sql: str) -> list[Row]:
        return self.check_read_only(sql)

    def syntax_row(self, problem: SyntaxProblemError) -> list[Row]:
        return [["syntax", str(problem)]]

    def check_access(self, sql: str) -> list[Row]:
        rows = self.read_only_gate(sql)
        if rows:
            return rows
        tokens, _ = self.scan(sql)
        try:
            query = self.parse(self.statements(tokens)[0])
        except SyntaxProblemError as problem:
            return self.syntax_row(problem)
        return self.access_rows(query)

    # ------------------------------------------------------------------ level 4
    def limited_sql(self, sql: str, max_rows: int) -> str:
        if self.check_access(sql):
            return self.refused(sql)
        return self.edit_limit(sql, max_rows)

    def refused(self, sql: str) -> str:
        return ""

    def edit_limit(self, sql: str, max_rows: int) -> str:
        tokens, _ = self.scan(sql)
        body = [t for t in tokens if t.kind not in ("comment", "semicolon")]
        limit = next(
            (i for i, t in enumerate(body) if t.kind == "keyword" and t.text == "LIMIT"), -1
        )
        offset = next(
            (i for i, t in enumerate(body) if t.kind == "keyword" and t.text == "OFFSET"), -1
        )
        if limit >= 0:
            return self.with_existing_limit(sql, body[limit + 1], max_rows)
        point = body[offset - 1].end if offset >= 0 else body[-1].end
        return self.insert_limit(sql, point, max_rows, tokens)

    def too_high(self, digits: str, max_rows: int) -> bool:
        return int(digits) > max_rows

    def with_existing_limit(self, sql: str, number: Tok, max_rows: int) -> str:
        if self.too_high(number.text, max_rows):
            return sql[: number.start] + str(max_rows) + sql[number.end :]
        return sql

    def insert_limit(self, sql: str, point: int, max_rows: int, tokens: list[Tok]) -> str:
        return sql[:point] + f" LIMIT {max_rows}" + sql[point:]

    def parse_for_literals(self, sql: str) -> Query | None:
        tokens, error = self.scan(sql)
        groups = self.statements(tokens)
        if error or len(groups) != 1:
            return None
        try:
            return self.parse(groups[0])
        except SyntaxProblemError:
            return None

    def literal_nodes(self, query: Query) -> list[Node]:
        found: list[Node] = []
        for node in [*query.conditions, query.where, query.having]:
            found.extend(self.literals_in(node))
        return found

    def literals_in(self, node: Node | None) -> list[Node]:
        if node is None:
            return []
        if node[0] == "lit":
            return [node]
        found: list[Node] = []
        for child in node[1:]:
            if isinstance(child, tuple):
                found.extend(self.literals_in(child))
            elif isinstance(child, list):
                for part in child:
                    if isinstance(part, tuple):
                        found.extend(self.literals_in(part))
        return found

    def literal_kind(self, text: str, user_values: list[str]) -> str:
        return "inlined-value" if text in user_values else "literal"

    def parameter_findings(self, sql: str, user_values: list[str]) -> list[Row]:
        query = self.parse_for_literals(sql)
        if query is None:
            return []
        rows = [[self.literal_kind(n[1], user_values), n[1]] for n in self.literal_nodes(query)]
        return self.dedupe(rows)


class _Parser:
    """Precedence climbing over the tokens of one statement, building a tree."""

    BINDING: ClassVar[dict[str, int]] = {"OR": 10, "AND": 20}

    def __init__(self, model: Model, tokens: list[Tok]) -> None:
        self.model = model
        self.tokens = tokens
        self.at = 0

    def look(self, ahead: int = 0) -> Tok | None:
        index = self.at + ahead
        return self.tokens[index] if index < len(self.tokens) else None

    def bad(self) -> SyntaxProblemError:
        token = self.look()
        return SyntaxProblemError(token.text if token else "end of input")

    def word(self, *words: str) -> bool:
        token = self.look()
        return bool(token and token.kind == "keyword" and token.text in words)

    def sym(self, *symbols: str) -> bool:
        token = self.look()
        return bool(token and token.kind == "symbol" and token.text in symbols)

    def take(self) -> Tok:
        token = self.look()
        if token is None:
            raise self.bad()
        self.at += 1
        return token

    def need_word(self, word: str) -> None:
        if not self.word(word):
            raise self.bad()
        self.at += 1

    def need_sym(self, symbol: str) -> None:
        if not self.sym(symbol):
            raise self.bad()
        self.at += 1

    def name(self) -> str:
        token = self.look()
        if token is None or token.kind != "identifier":
            raise self.bad()
        self.at += 1
        return token.text.lower()

    def alias(self) -> str | None:
        if self.word("AS"):
            self.at += 1
            return self.name()
        token = self.look()
        return self.name() if token and token.kind == "identifier" else None

    # --- the query
    def query(self) -> Query:
        self.need_word("SELECT")
        if self.word("DISTINCT"):
            self.at += 1
        items = self.items()
        sources: list[tuple[str, str]] = []
        conditions: list[Node] = []
        if self.word("FROM"):
            self.at += 1
            self.sources(sources, conditions)
        where = self.clause("WHERE")
        group: list[Node] = []
        if self.word("GROUP"):
            self.at += 1
            self.need_word("BY")
            group = self.expression_list()
        having = self.clause("HAVING")
        order: list[Node] = []
        if self.word("ORDER"):
            self.at += 1
            self.need_word("BY")
            order = self.order_items()
        if self.word("LIMIT"):
            self.at += 1
            self.integer()
        if self.word("OFFSET"):
            self.at += 1
            self.integer()
        if self.look() is not None:
            raise self.bad()
        return Query(items, sources, conditions, where, group, having, order)

    def integer(self) -> None:
        token = self.look()
        if token is None or token.kind != "number" or not re.fullmatch(r"[0-9]+", token.text):
            raise self.bad()
        self.at += 1

    def clause(self, word: str) -> Node | None:
        if not self.word(word):
            return None
        self.at += 1
        return self.expression()

    def items(self) -> list[tuple[Node | None, str | None]]:
        found: list[tuple[Node | None, str | None]] = []
        while True:
            if self.sym("*"):
                self.at += 1
                found.append((None, None))
            else:
                node = self.expression()
                found.append((node, self.alias()))
            if not self.sym(","):
                return found
            self.at += 1

    def sources(self, sources: list[tuple[str, str]], conditions: list[Node]) -> None:
        self.source(sources)
        while True:
            if self.sym(","):
                self.at += 1
                self.source(sources)
            elif self.word("INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN"):
                self.join_word()
                self.source(sources)
                if self.word("ON"):
                    self.at += 1
                    conditions.append(self.expression())
            else:
                return

    def join_word(self) -> None:
        first = self.take()
        if first.text == "JOIN":
            return
        if first.text in ("LEFT", "RIGHT", "FULL") and self.word("OUTER"):
            self.at += 1
        self.need_word("JOIN")

    def source(self, sources: list[tuple[str, str]]) -> None:
        table = self.name()
        alias = self.alias()
        sources.append((alias or table, table))

    def order_items(self) -> list[Node]:
        found: list[Node] = []
        while True:
            found.append(self.expression())
            if self.word("ASC", "DESC"):
                self.at += 1
            if not self.sym(","):
                return found
            self.at += 1

    def expression_list(self) -> list[Node]:
        found = [self.expression()]
        while self.sym(","):
            self.at += 1
            found.append(self.expression())
        return found

    # --- expressions
    def expression(self, floor: int = 0) -> Node:
        left = self.prefix()
        predicated = False
        while True:
            token = self.look()
            if token is None:
                return left
            power = self.power(token)
            if power <= floor:
                return left
            if power == PREDICATE_BP:
                if predicated:
                    return left
                left = self.predicate(left)
                predicated = True
            else:
                self.at += 1
                left = (token.text, left, self.expression(power))

    def power(self, token: Tok) -> int:
        if token.kind == "keyword":
            if token.text in self.BINDING:
                return self.BINDING[token.text]
            if token.text in ("IS", "LIKE", "IN", "BETWEEN", "NOT"):
                return PREDICATE_BP
        if token.kind == "symbol":
            if token.text in ("=", "<>", "!=", "<", "<=", ">", ">="):
                return PREDICATE_BP
            if token.text in ("+", "-", "||"):
                return 50
            if token.text in ("*", "/", "%"):
                return 60
        return 0

    def predicate(self, left: Node) -> Node:
        token = self.take()
        if token.kind == "symbol":
            return ("cmp", left, self.expression(PREDICATE_BP))
        word = token.text
        if word == "NOT" and token.kind == "keyword":
            if not self.word("LIKE", "IN", "BETWEEN"):
                raise self.bad()
            word = self.take().text
        elif word == "IS":
            if self.word("NOT"):
                self.at += 1
            self.need_word("NULL")
            return ("is", left)
        if word == "LIKE":
            return ("like", left, self.expression(PREDICATE_BP))
        if word == "IN":
            self.need_sym("(")
            members = self.expression_list()
            self.need_sym(")")
            return ("in", left, members)
        low = self.expression(PREDICATE_BP)
        self.need_word("AND")
        return ("between", left, low, self.expression(PREDICATE_BP))

    def prefix(self) -> Node:
        token = self.look()
        if token is None:
            raise self.bad()
        if token.kind == "keyword" and token.text == "NOT":
            self.at += 1
            return ("not", self.expression(30))
        if token.kind == "symbol" and token.text in ("-", "+"):
            self.at += 1
            return ("sign", self.expression(70))
        return self.primary(token)

    def primary(self, token: Tok) -> Node:
        if token.kind in ("number", "string"):
            self.at += 1
            return ("lit", token.text)
        if token.kind == "placeholder":
            self.at += 1
            return ("ph", token.text)
        if token.kind == "keyword" and token.text in ("TRUE", "FALSE", "NULL"):
            self.at += 1
            return ("const", token.text)
        if token.kind == "symbol" and token.text == "(":
            self.at += 1
            inner = self.expression()
            self.need_sym(")")
            return ("paren", inner)
        if token.kind != "identifier":
            raise self.bad()
        following = self.look(1)
        if following and following.kind == "symbol" and following.text == "(":
            return self.call()
        self.at += 1
        if self.sym("."):
            self.at += 1
            return ("col", token.text.lower(), self.name())
        return ("col", None, token.text.lower())

    def call(self) -> Node:
        name = self.take().text.lower()
        self.at += 1
        arguments: list[Node] = []
        if self.model.model_strict(name):
            arguments = self.strict_arguments(name)
        elif self.sym("*"):
            self.at += 1
        elif not self.sym(")"):
            if self.word("DISTINCT"):
                self.at += 1
            arguments = self.expression_list()
        self.need_sym(")")
        return ("call", name, arguments)

    def strict_arguments(self, name: str) -> list[Node]:
        if self.sym("*"):
            if name != "count":
                raise self.bad()
            self.at += 1
            return []
        if self.sym(")"):
            raise self.bad()
        if self.word("DISTINCT"):
            self.at += 1
        return [self.expression()]


# ------------------------------------------------------------------ level 1 mistakes
class StringEndsAtDoubledQuote(Model):
    """Ends a string at the first quote, so a doubled quote is two strings."""

    STRING = re.compile(r"'[^']*'")


class BackslashEscapesAQuote(Model):
    """Reads a backslash as an escape in a string."""

    STRING = re.compile(r"'(?:\\.|[^'\\]|'')*+'")

    def decode_string(self, raw: str) -> str:
        return raw[1:-1].replace("''", "'").replace("\\'", "'")


class StringKeepsDoubledQuotes(Model):
    """Leaves each doubled quote of a string as two."""

    def decode_string(self, raw: str) -> str:
        return raw[1:-1]


class NameKeepsDoubledQuotes(Model):
    """Leaves each doubled quote of a quoted name as two."""

    def decode_name(self, raw: str) -> str:
        return raw[1:-1]


class UnterminatedStringAccepted(Model):
    """Takes an unfinished string up to the end of the text."""

    def read_string(self, sql: str, pos: int) -> tuple[str, int]:
        try:
            return super().read_string(sql, pos)
        except LexError:
            return sql[pos + 1 :], len(sql)


class BlockCommentsNest(Model):
    """Closes a block comment at the matching mark, as some databases do."""

    def block_comment_end(self, sql: str, pos: int) -> int:
        depth = 0
        i = pos
        while i < len(sql) - 1:
            if sql[i : i + 2] == "/*":
                depth += 1
                i += 2
            elif sql[i : i + 2] == "*/":
                depth -= 1
                i += 2
                if depth == 0:
                    return i
            else:
                i += 1
        return -1


class SlashStarSlashIsAComment(Model):
    """Lets the star of the opening mark close the comment."""

    def block_comment_end(self, sql: str, pos: int) -> int:
        found = sql.find("*/", pos + 1)
        return -1 if found < 0 else found + 2


class LineCommentTakesTheLineBreak(Model):
    """Lets a line comment swallow the line break."""

    LINE = re.compile(r"--[^\n\r]*\r?\n?")


class KeywordsOnlyInCapitals(Model):
    """Reads a word as a keyword only when it is written in capitals."""

    def word_token(self, word: str, start: int, end: int) -> Tok:
        if word in QUERY_WORDS | self.FORBIDDEN:
            return Tok("keyword", word, start, end)
        return Tok("identifier", word, start, end)


class KeywordTextAsWritten(Model):
    """Keeps a keyword as it was written."""

    def word_token(self, word: str, start: int, end: int) -> Tok:
        token = super().word_token(word, start, end)
        return Tok(token.kind, word if token.kind == "keyword" else token.text, start, end)


class QuotedNameCanBeAKeyword(Model):
    """Reads a quoted name as a keyword when its text is one."""

    def read_quoted(self, sql: str, pos: int) -> tuple[Tok, int]:
        token, end = super().read_quoted(sql, pos)
        if token.text.upper() in QUERY_WORDS | self.FORBIDDEN:
            return Tok("keyword", token.text.upper(), pos, end), end
        return token, end


class NumbersTakeASign(Model):
    """Reads a minus sign before digits as part of the number."""

    NUMBER = re.compile(r"-?[0-9]+(?:\.[0-9]+)?|\.[0-9]+")


class LeadingPointIsNotANumber(Model):
    """Wants a digit before the point of a number."""

    NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")


class TrailingPointJoinsTheNumber(Model):
    """Takes a point after the digits into the number."""

    NUMBER = re.compile(r"[0-9]+\.?[0-9]*|\.[0-9]+")


class NumberGluedToAWordIsTwoTokens(Model):
    """Does not complain when a number is followed by a letter."""

    def number_may_continue(self, sql: str, end: int) -> bool:
        return False


class PrefixedStringsAccepted(Model):
    """Reads E'x' as a word and a string."""

    def prefix_forbidden(self, word: str, sql: str, end: int) -> bool:
        return False


class PrefixCheckedOnAnyWord(Model):
    """Refuses any word that is directly followed by a quote."""

    def prefix_forbidden(self, word: str, sql: str, end: int) -> bool:
        return sql[end : end + 1] == "'"


class TwoCharacterSymbolsSplit(Model):
    """Reads every symbol as one character."""

    SYMBOL = re.compile(r"[(),.*+\-/%=<>|!]")


class OnlyQuestionPlaceholders(Model):
    """Knows the marker ? and no other."""

    PLACEHOLDER = re.compile(r"\?")


class CommentsAreNotListed(Model):
    """Leaves the comments out of the tokens."""

    def listed(self, tokens: list[Tok]) -> list[Tok]:
        return [t for t in tokens if t.kind != "comment"]


class ErrorRowLeftOut(Model):
    """Stops at a lexical error without saying so."""

    def tokenize(self, sql: str) -> list[Row]:
        return super().tokenize(sql)[: len(self.listed(self.scan(sql)[0]))]


class EmptyStatementsAreCounted(Model):
    """Counts the empty group after a semicolon, except at the very end."""

    def statement_count(self, sql: str, tokens: list[Tok]) -> int:
        groups: list[list[Tok]] = [[]]
        for token in tokens:
            if token.kind == "semicolon":
                groups.append([])
            elif token.kind != "comment":
                groups[-1].append(token)
        if not groups[-1]:
            groups.pop()
        return len(groups)


class SemicolonInTextSplits(Model):
    """Counts every semicolon of the raw text."""

    def statement_count(self, sql: str, tokens: list[Tok]) -> int:
        return (
            sql.strip().rstrip(";").count(";") + 1
            if any(t.kind != "comment" for t in tokens)
            else 0
        )


class CommentOnlyTextIsAStatement(Model):
    """Counts a text of comments as a statement."""

    def statement_count(self, sql: str, tokens: list[Tok]) -> int:
        count = len(self.statements(tokens))
        return count if count else int(any(t.kind == "comment" for t in tokens))


class LexicalErrorIsNotAFinding(Model):
    """Counts statements on the tokens before a lexical error."""

    def lex_errors_count(self) -> bool:
        return False


class NothingToCheckPasses(Model):
    """Accepts a text with no statement."""

    def when_empty(self) -> list[Row]:
        return []


# ------------------------------------------------------------------ level 2 mistakes
class ReadOnlyBySubstring(Model):
    """Searches the raw text for the naive words."""

    def read_only_tail(self, sql: str, tokens: list[Tok]) -> list[Row]:
        return [["forbidden-keyword", w.upper()] for w in NAIVE_LIST if w in sql.lower()]


class ForbiddenWordsInStrings(Model):
    """Looks for forbidden words in strings and comments too."""

    def forbidden_rows(self, tokens: list[Tok]) -> list[Row]:
        rows = super().forbidden_rows(tokens)
        for t in tokens:
            for word in re.findall(
                r"[A-Za-z_]+", t.text if t.kind in ("string", "comment") else ""
            ):
                if word.upper() in self.FORBIDDEN:
                    rows.append(["forbidden-keyword", word.upper()])
        return rows


class OnlyTheFirstStatementIsChecked(Model):
    """Looks at the first word of the first statement only."""

    def not_select_rows(self, sql: str, groups: list[list[Tok]]) -> list[Row]:
        return super().not_select_rows(sql, groups[:1])


class WithIsAllowed(Model):
    """Lets a query start with WITH."""

    def first_is_select(self, sql: str, first: Tok) -> bool:
        return first.kind == "keyword" and first.text in ("SELECT", "WITH")


class IntoIsAllowed(Model):
    """Leaves INTO out of the forbidden words."""

    FORBIDDEN = FORBIDDEN_WORDS - {"INTO"}


class ForbiddenListIsShort(Model):
    """Forbids the four classic words only."""

    FORBIDDEN = frozenset({"INSERT", "UPDATE", "DELETE", "DROP"})


class SetAndReplaceAreAllowed(Model):
    """Leaves out the words that also have harmless uses."""

    FORBIDDEN = FORBIDDEN_WORDS - {"SET", "REPLACE"}


class ExecutableCommentsAreIgnored(Model):
    """Skips every comment."""

    def is_executable(self, comment: str) -> bool:
        return False


class EveryBlockCommentIsRefused(Model):
    """Refuses any block comment."""

    def is_executable(self, comment: str) -> bool:
        return comment.startswith("/*")


class ExecutableMarkAnywhere(Model):
    """Looks for the mark in the raw text, strings included."""

    def executable_rows(self, sql: str, tokens: list[Tok]) -> list[Row]:
        return [["executable-comment", ""]] if "/*!" in sql else []


class ReadOnlyRowsRepeat(Model):
    """Keeps a row that comes twice."""

    def dedupe(self, rows: list[Row]) -> list[Row]:
        return rows


class QuotedWordsAreForbidden(Model):
    """Checks the text of every name against the forbidden words."""

    def forbidden_rows(self, tokens: list[Tok]) -> list[Row]:
        return [
            ["forbidden-keyword", t.text.upper()]
            for t in tokens
            if t.kind in ("keyword", "identifier") and t.text.upper() in self.FORBIDDEN
        ]


class SelectIsMatchedByItsSpelling(Model):
    """Wants the first word to be written SELECT in capitals."""

    def first_is_select(self, sql: str, first: Tok) -> bool:
        return sql[first.start : first.end] == "SELECT"


class ForbiddenBeforeNotSelect(Model):
    """Lists the forbidden words before the first-word rows."""

    def read_only_tail(self, sql: str, tokens: list[Tok]) -> list[Row]:
        return [
            *self.forbidden_rows(tokens),
            *self.not_select_rows(sql, self.statements(tokens)),
            *self.executable_rows(sql, tokens),
        ]


class ReadOnlyHidesTheCount(Model):
    """Leaves the statement-count row out of the answer."""

    def check_read_only(self, sql: str) -> list[Row]:
        return [r for r in super().check_read_only(sql) if r[0] != "multiple-statements"]


class NaiveCheckIsCaseSensitive(Model):
    """Searches the words as written."""

    def naive_check(self, sql: str) -> str:
        return "reject" if any(word in sql for word in self.NAIVE) else "allow"


class NaiveListIsShort(Model):
    """Leaves one word out of the naive list."""

    NAIVE = NAIVE_LIST[:-1]


class ContrastSwapsTheNames(Model):
    """Calls a false alarm a miss."""

    def contrast(self, sql: str) -> str:
        answer = super().contrast(sql)
        return {"false-alarm": "miss", "miss": "false-alarm"}.get(answer, answer)


class ContrastComparesWithCheck(Model):
    """Compares the naive check with the statement count only."""

    def contrast(self, sql: str) -> str:
        naive = self.naive_check(sql)
        guard = "reject" if self.check(sql) else "allow"
        if naive == guard:
            return "agree"
        return "false-alarm" if naive == "reject" else "miss"


# ------------------------------------------------------------------ level 3 mistakes
class TableNamesKeepCase(Model):
    """Folds nothing when a table is allowed."""

    def allow_table(self, table: str, columns: list[str]) -> bool:
        if table in self.allowed:
            return False
        self.allowed[table] = {c.lower() for c in columns}
        return True


class ColumnNamesKeepCase(Model):
    """Folds the table but not the columns."""

    def allow_table(self, table: str, columns: list[str]) -> bool:
        if table.lower() in self.allowed:
            return False
        self.allowed[table.lower()] = set(columns)
        return True


class AllowTableReplaces(Model):
    """Replaces the columns of a table that is already allowed."""

    def allow_table(self, table: str, columns: list[str]) -> bool:
        new = table.lower() not in self.allowed
        self.allowed[table.lower()] = {c.lower() for c in columns}
        return new


class AllowTableMerges(Model):
    """Adds the columns to a table that is already allowed."""

    def allow_table(self, table: str, columns: list[str]) -> bool:
        key = table.lower()
        new = key not in self.allowed
        self.allowed.setdefault(key, set()).update(c.lower() for c in columns)
        return new


class WildcardIsAllowed(Model):
    """Lets * through."""

    def wildcard_rows(self) -> list[Row]:
        return []


class EveryFunctionIsAllowed(Model):
    """Lets any call through."""

    def function_rows(self, name: str) -> list[Row]:
        return []


class AggregateShapeIsNotChecked(Model):
    """Reads an aggregate like any other call."""

    def model_strict(self, name: str) -> bool:
        return False


class TableNameStillNamesAnAliasedTable(Model):
    """Accepts the table name as a qualifier after an alias."""

    def source_table(self, qualifier: str, sources: list[tuple[str, str]]) -> str | None:
        return super().source_table(qualifier, sources) or next(
            (t for _, t in sources if t == qualifier), None
        )


class AliasesAreVisibleEverywhere(Model):
    """Lets an output alias stand for a column in any clause."""

    def events(self, query: Query) -> list[Node]:
        aliases = {alias for _, alias in query.items if alias}
        return [
            e
            for e in super().events(query)
            if not (e[0] == "col" and e[1] is None and e[2] in aliases)
        ]


class AliasesAreVisibleInOrderExpressions(Model):
    """Lets an alias appear inside a bigger ORDER BY expression."""

    def order_events(self, order: list[Node], aliases: set[str]) -> list[Node]:
        return [
            e
            for node in order
            for e in self.walk(node)
            if not (e[0] == "col" and e[1] is None and e[2] in aliases)
        ]


class AmbiguityIsNotReported(Model):
    """Takes any source that has the column."""

    def reports_ambiguity(self) -> bool:
        return False


class UnqualifiedCascades(Model):
    """Reports a column even when a table that is not allowed may hold it."""

    def unknown_may_hide(self, sources: list[tuple[str, str]]) -> bool:
        return False


class UnqualifiedGivesUpWithoutAnAllowedSource(Model):
    """Says nothing about a column when no source is allowed, and also when some are."""

    def unknown_may_hide(self, sources: list[tuple[str, str]]) -> bool:
        return any(table in self.allowed for _, table in sources) or not sources


class ColumnsBeforeTables(Model):
    """Lists the name findings before the table findings."""

    def arrange(self, tables: list[Row], others: list[Row]) -> list[Row]:
        return self.dedupe(others + tables)


class DuplicateSourceIsNotReported(Model):
    """Lets a source name be used twice."""

    def duplicate_of(self, name: str, used: list[str]) -> bool:
        return False


class ColumnsOfADisallowedTableAreChecked(Model):
    """Reports the columns of a table that is not allowed."""

    def allowed_columns(self, table: str) -> set[str] | None:
        return self.allowed.get(table, set())


class QualifiedDetailIsTheColumn(Model):
    """Leaves the qualifier out of the detail."""

    def qualified_detail(self, qualifier: str, name: str) -> str:
        return name


class AccessSkipsTheReadOnlyRules(Model):
    """Goes straight to the grammar after the scanner."""

    def read_only_gate(self, sql: str) -> list[Row]:
        tokens, error = self.scan(sql)
        if error:
            return [["lex-error", error]]
        return [] if self.statements(tokens) else [["empty", ""]]


class AccessRowsRepeat(Model):
    """Keeps a finding that comes twice."""

    def arrange(self, tables: list[Row], others: list[Row]) -> list[Row]:
        return tables + others


class SyntaxNamesTheFirstToken(Model):
    """Reports the first token of the statement."""

    def syntax_row(self, problem: SyntaxProblemError) -> list[Row]:
        return [["syntax", "SELECT"]]


class SyntaxAtTheEndIsEmpty(Model):
    """Says nothing when the text ends too soon."""

    def syntax_row(self, problem: SyntaxProblemError) -> list[Row]:
        return [["syntax", "" if str(problem) == "end of input" else str(problem)]]


class NoTableIsEverRefused(Model):
    """Allows every table."""

    def source_rows(self, sources: list[tuple[str, str]]) -> list[Row]:
        return []


class NamesInDetailsKeepTheirCase(Model):
    """Reports a name as it was written."""

    def qualified_detail(self, qualifier: str, name: str) -> str:
        return f"{qualifier.upper()}.{name.upper()}"


# ------------------------------------------------------------------ level 4 mistakes
class LimitIsAppendedAtTheEnd(Model):
    """Adds the limit at the end of the text, after a comment or a semicolon."""

    def insert_limit(self, sql: str, point: int, max_rows: int, tokens: list[Tok]) -> str:
        return sql + f" LIMIT {max_rows}"


class LimitGoesBeforeTheFirstSemicolon(Model):
    """Adds the limit at the semicolon, or at the end, after a comment."""

    def insert_limit(self, sql: str, point: int, max_rows: int, tokens: list[Tok]) -> str:
        semicolons = [t.start for t in tokens if t.kind == "semicolon"]
        at = semicolons[0] if semicolons else len(sql)
        return sql[:at] + f" LIMIT {max_rows}" + sql[at:]


class LimitGoesAfterTheOffset(Model):
    """Adds the limit at the end of the query body, after an offset."""

    def edit_limit(self, sql: str, max_rows: int) -> str:
        tokens, _ = self.scan(sql)
        body = [t for t in tokens if t.kind not in ("comment", "semicolon")]
        if any(t.kind == "keyword" and t.text == "LIMIT" for t in body):
            return super().edit_limit(sql, max_rows)
        return sql[: body[-1].end] + f" LIMIT {max_rows}" + sql[body[-1].end :]


class LimitIsNeverLowered(Model):
    """Adds a limit but keeps a larger one."""

    def too_high(self, digits: str, max_rows: int) -> bool:
        return False


class LimitIsAlwaysReplaced(Model):
    """Writes the maximum over any limit."""

    def too_high(self, digits: str, max_rows: int) -> bool:
        return True


class LimitIsComparedAsText(Model):
    """Compares the digits as text."""

    def too_high(self, digits: str, max_rows: int) -> bool:
        return digits > str(max_rows)


class LimitIsRewrittenAsANumber(Model):
    """Writes a low limit back without its leading zeros."""

    def with_existing_limit(self, sql: str, number: Tok, max_rows: int) -> str:
        value = min(int(number.text), max_rows)
        return sql[: number.start] + str(value) + sql[number.end :]


class LimitIsFoundInTheRawText(Model):
    """Replaces the first 'limit' followed by digits anywhere in the text."""

    def edit_limit(self, sql: str, max_rows: int) -> str:
        found = re.search(r"(?i)limit\s+([0-9]+)", sql)
        if found is None:
            return super().edit_limit(sql, max_rows)
        if int(found.group(1)) > max_rows:
            return sql[: found.start(1)] + str(max_rows) + sql[found.end(1) :]
        return sql


class RefusedQueryIsReturnedAsItIs(Model):
    """Gives the text back when it is refused."""

    def refused(self, sql: str) -> str:
        return sql


class LimitSkipsTheGrammar(Model):
    """Edits any query that passes the read-only rules."""

    def limited_sql(self, sql: str, max_rows: int) -> str:
        if self.read_only_gate(sql):
            return ""
        return self.edit_limit(sql, max_rows)


class LimitSkipsTheAllowlist(Model):
    """Edits any query that fits the grammar."""

    def limited_sql(self, sql: str, max_rows: int) -> str:
        if self.read_only_gate(sql) or self.parse_for_literals(sql) is None:
            return ""
        return self.edit_limit(sql, max_rows)


class NoValueIsEverInlined(Model):
    """Marks every literal as a constant."""

    def literal_kind(self, text: str, user_values: list[str]) -> str:
        return "literal"


class EveryLiteralIsInlined(Model):
    """Marks every literal as a user value."""

    def literal_kind(self, text: str, user_values: list[str]) -> str:
        return "inlined-value"


class UserValuesIgnoreCase(Model):
    """Compares the values without regard to case."""

    def literal_kind(self, text: str, user_values: list[str]) -> str:
        return "inlined-value" if text.lower() in [v.lower() for v in user_values] else "literal"


class LiteralsOutsideConditionsCount(Model):
    """Reports the literals of the select list and of the clauses too."""

    def literal_nodes(self, query: Query) -> list[Node]:
        found = super().literal_nodes(query)
        for item, _ in query.items:
            found.extend(self.literals_in(item))
        for node in [*query.group, *query.order]:
            found.extend(self.literals_in(node))
        return found


class HavingLiteralsAreNotChecked(Model):
    """Reads WHERE and ON only."""

    def literal_nodes(self, query: Query) -> list[Node]:
        return [n for c in [*query.conditions, query.where] for n in self.literals_in(c)]


class OnLiteralsAreNotChecked(Model):
    """Reads WHERE and HAVING only."""

    def literal_nodes(self, query: Query) -> list[Node]:
        return [n for c in [query.where, query.having] for n in self.literals_in(c)]


class LiteralsRepeat(Model):
    """Keeps a literal that comes twice."""

    def dedupe(self, rows: list[Row]) -> list[Row]:
        return rows


class LiteralsAreSorted(Model):
    """Lists the findings sorted, not in the order of the text."""

    def parameter_findings(self, sql: str, user_values: list[str]) -> list[Row]:
        return sorted(super().parameter_findings(sql, user_values))


class OnlyStringsAreLiterals(Model):
    """Counts string tokens but not numbers."""

    def literal_nodes(self, query: Query) -> list[Node]:
        return [n for n in super().literal_nodes(query) if not re.fullmatch(r"[0-9.]+", n[1])]


class ParametersAreFoundInBrokenText(Model):
    """Looks for quoted values in a text that does not parse."""

    def parameter_findings(self, sql: str, user_values: list[str]) -> list[Row]:
        rows = super().parameter_findings(sql, user_values)
        if rows or self.parse_for_literals(sql) is not None:
            return rows
        tokens, _ = self.scan(sql)
        return [
            [self.literal_kind(t.text, user_values), t.text]
            for t in tokens
            if t.kind in ("string", "number")
        ]


class SignedValuesMatch(Model):
    """Lets a user value written with a minus sign match its digits."""

    def literal_kind(self, text: str, user_values: list[str]) -> str:
        return "inlined-value" if text in [v.lstrip("-") for v in user_values] else "literal"


MISTAKES: Sequence[type[Model]] = [
    subclass for subclass in Model.__subclasses__() if subclass.__module__ == __name__
]


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: Callable[[], Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: Callable[[], Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (
        IndexError,
        KeyError,
        ValueError,
        TypeError,
        RecursionError,
        LexError,
        SyntaxProblemError,
    ):
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


def hidden_values(op: str, column: int) -> set[str]:
    """The values in a column of the rows that the hidden cases expect from one method."""
    found: set[str] = set()
    for case in HIDDEN_CASES:
        for name, got in zip(case["ops"], case["expected"], strict=True):
            if name == op:
                found.update(row[column] for row in got)
    return found


def test_the_hidden_cases_reach_every_code_of_every_answer():
    assert hidden_values("tokenize", 0) >= {
        "keyword",
        "identifier",
        "string",
        "number",
        "symbol",
        "placeholder",
        "semicolon",
        "comment",
        "error",
    }
    assert {
        row[1]
        for case in HIDDEN_CASES
        for name, got in zip(case["ops"], case["expected"], strict=True)
        if name == "tokenize"
        for row in got
        if row[0] == "error"
    } == {
        "unterminated-string",
        "unterminated-identifier",
        "empty-identifier",
        "unterminated-comment",
        "malformed-number",
        "prefixed-string",
        "unexpected-character",
    }
    assert hidden_values("check", 0) == {"lex-error", "empty", "multiple-statements"}
    assert hidden_values("checkReadOnly", 0) >= {
        "not-select",
        "forbidden-keyword",
        "executable-comment",
    }
    assert hidden_values("checkAccess", 0) >= {
        "syntax",
        "table-not-allowed",
        "duplicate-source",
        "wildcard-not-allowed",
        "function-not-allowed",
        "unknown-source",
        "column-not-allowed",
        "ambiguous-column",
    }
    assert hidden_values("parameterFindings", 0) == {"inlined-value", "literal"}


def test_the_hidden_cases_give_every_answer_of_contrast():
    answers = {
        got
        for case in HIDDEN_CASES
        for name, got in zip(case["ops"], case["expected"], strict=True)
        if name == "contrast"
    }
    assert answers == {"agree", "false-alarm", "miss"}
