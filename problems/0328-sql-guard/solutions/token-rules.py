from dataclasses import dataclass

GRAMMAR_KEYWORDS = frozenset(
    "SELECT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET AS JOIN INNER LEFT RIGHT FULL OUTER "
    "CROSS ON AND OR NOT NULL IS IN LIKE BETWEEN DISTINCT ASC DESC UNION ALL TRUE FALSE WITH".split()
)
FORBIDDEN_KEYWORDS = frozenset(
    "INSERT UPDATE DELETE MERGE REPLACE DROP CREATE ALTER TRUNCATE RENAME GRANT REVOKE CALL "
    "EXEC EXECUTE COPY ATTACH DETACH PRAGMA VACUUM SET INTO".split()
)
KEYWORDS = GRAMMAR_KEYWORDS | FORBIDDEN_KEYWORDS
AGGREGATES = frozenset({"count", "sum", "avg", "min", "max"})
NAIVE_WORDS = ("insert", "update", "delete", "drop", "alter", "create", "truncate")
STRING_PREFIXES = "ENXBenxb"
TWO_CHAR_SYMBOLS = ("<=", ">=", "<>", "!=", "||")
ONE_CHAR_SYMBOLS = "(),.*+-/%=<>"
BLANKS = " \t\n\r"
COMPARISONS = ("=", "<>", "!=", "<", "<=", ">", ">=")
JOIN_STARTS = ("INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN")
END_OF_INPUT = "end of input"


def _is_digit(char: str) -> bool:
    return "0" <= char <= "9"


def _is_word_start(char: str) -> bool:
    return "a" <= char <= "z" or "A" <= char <= "Z" or char == "_"


def _is_word_char(char: str) -> bool:
    return _is_word_start(char) or _is_digit(char)


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    start: int
    end: int


def _scan_quoted(sql: str, start: int, quote: str) -> tuple[str, int] | None:
    """The decoded content of a quoted piece that opens at `start`, and the index after it."""
    chars: list[str] = []
    i = start + 1
    while i < len(sql):
        if sql[i] == quote:
            if sql[i + 1 : i + 2] == quote:
                chars.append(quote)
                i += 2
                continue
            return "".join(chars), i + 1
        chars.append(sql[i])
        i += 1
    return None


def _scan_number(sql: str, start: int) -> int:
    """The index after the number at `start`: digits, then optionally a point and digits."""
    i = start
    while i < len(sql) and _is_digit(sql[i]):
        i += 1
    if sql[i : i + 1] == "." and _is_digit(sql[i + 1 : i + 2]):
        i += 1
        while i < len(sql) and _is_digit(sql[i]):
            i += 1
    return i


def _scan_word(sql: str, start: int) -> int:
    i = start
    while i < len(sql) and _is_word_char(sql[i]):
        i += 1
    return i


def lex(sql: str) -> tuple[list[Token], str]:
    """Every token up to the first lexical error, and the error code ("" when there is none)."""
    tokens: list[Token] = []
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]
        if c in BLANKS:
            i += 1
        elif sql.startswith("--", i):
            j = i
            while j < n and sql[j] not in "\n\r":
                j += 1
            tokens.append(Token("comment", sql[i:j], i, j))
            i = j
        elif sql.startswith("/*", i):
            close = sql.find("*/", i + 2)
            if close < 0:
                return tokens, "unterminated-comment"
            tokens.append(Token("comment", sql[i : close + 2], i, close + 2))
            i = close + 2
        elif c == "'":
            scanned = _scan_quoted(sql, i, "'")
            if scanned is None:
                return tokens, "unterminated-string"
            tokens.append(Token("string", scanned[0], i, scanned[1]))
            i = scanned[1]
        elif c == '"':
            scanned = _scan_quoted(sql, i, '"')
            if scanned is None:
                return tokens, "unterminated-identifier"
            if scanned[0] == "":
                return tokens, "empty-identifier"
            tokens.append(Token("identifier", scanned[0], i, scanned[1]))
            i = scanned[1]
        elif _is_digit(c) or (c == "." and i + 1 < n and _is_digit(sql[i + 1])):
            j = _scan_number(sql, i)
            if j < n and _is_word_char(sql[j]):
                return tokens, "malformed-number"
            tokens.append(Token("number", sql[i:j], i, j))
            i = j
        elif _is_word_start(c):
            j = _scan_word(sql, i)
            word = sql[i:j]
            if len(word) == 1 and word in STRING_PREFIXES and sql[j : j + 1] == "'":
                return tokens, "prefixed-string"
            if word.upper() in KEYWORDS:
                tokens.append(Token("keyword", word.upper(), i, j))
            else:
                tokens.append(Token("identifier", word, i, j))
            i = j
        elif c == ";":
            tokens.append(Token("semicolon", ";", i, i + 1))
            i += 1
        elif c == "?":
            tokens.append(Token("placeholder", "?", i, i + 1))
            i += 1
        elif c == "$" and i + 1 < n and _is_digit(sql[i + 1]):
            j = i + 1
            while j < n and _is_digit(sql[j]):
                j += 1
            tokens.append(Token("placeholder", sql[i:j], i, j))
            i = j
        elif c == ":" and i + 1 < n and _is_word_start(sql[i + 1]):
            j = _scan_word(sql, i + 1)
            tokens.append(Token("placeholder", sql[i:j], i, j))
            i = j
        elif sql[i : i + 2] in TWO_CHAR_SYMBOLS:
            tokens.append(Token("symbol", sql[i : i + 2], i, i + 2))
            i += 2
        elif c in ONE_CHAR_SYMBOLS:
            tokens.append(Token("symbol", c, i, i + 1))
            i += 1
        else:
            return tokens, "unexpected-character"
    return tokens, ""


def _statements(tokens: list[Token]) -> list[list[Token]]:
    """The non-empty statements: the tokens between semicolons, comments left out."""
    groups: list[list[Token]] = [[]]
    for token in tokens:
        if token.kind == "semicolon":
            groups.append([])
        elif token.kind != "comment":
            groups[-1].append(token)
    return [group for group in groups if group]


def _distinct(rows: list[list[str]]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    kept: list[list[str]] = []
    for row in rows:
        if tuple(row) not in seen:
            seen.add(tuple(row))
            kept.append(row)
    return kept


class _Syntax(Exception):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


@dataclass
class _Parsed:
    tables: list[tuple[str, str]]
    events: list[tuple]
    condition_literals: list[str]
    limit: Token | None
    offset: Token | None
    before_offset: int
    last: Token


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.tables: list[tuple[str, str]] = []
        self.events: list[tuple] = []
        self.aliases: set[str] = set()
        self.condition_literals: list[str] = []
        self.in_condition = False
        self.limit: Token | None = None
        self.offset: Token | None = None
        self.before_offset = 0

    # --- helpers
    def peek(self, ahead: int = 0) -> Token | None:
        index = self.pos + ahead
        return self.tokens[index] if index < len(self.tokens) else None

    def fail(self) -> _Syntax:
        token = self.peek()
        return _Syntax(token.text if token else END_OF_INPUT)

    def is_keyword(self, *names: str) -> bool:
        token = self.peek()
        return token is not None and token.kind == "keyword" and token.text in names

    def is_symbol(self, *texts: str) -> bool:
        token = self.peek()
        return token is not None and token.kind == "symbol" and token.text in texts

    def take(self) -> Token:
        token = self.peek()
        if token is None:
            raise self.fail()
        self.pos += 1
        return token

    def expect_keyword(self, name: str) -> Token:
        if not self.is_keyword(name):
            raise self.fail()
        return self.take()

    def expect_symbol(self, text: str) -> Token:
        if not self.is_symbol(text):
            raise self.fail()
        return self.take()

    def expect_identifier(self) -> Token:
        token = self.peek()
        if token is None or token.kind != "identifier":
            raise self.fail()
        return self.take()

    def maybe_alias(self) -> str | None:
        if self.is_keyword("AS"):
            self.take()
            return self.expect_identifier().text.lower()
        token = self.peek()
        if token is not None and token.kind == "identifier":
            return self.take().text.lower()
        return None

    # --- the query
    def parse(self) -> _Parsed:
        self.expect_keyword("SELECT")
        if self.is_keyword("DISTINCT"):
            self.take()
        self.select_list()
        if self.is_keyword("FROM"):
            self.take()
            self.from_list()
        if self.is_keyword("WHERE"):
            self.take()
            self.condition()
        if self.is_keyword("GROUP"):
            self.take()
            self.expect_keyword("BY")
            self.expression_list()
        if self.is_keyword("HAVING"):
            self.take()
            self.condition()
        if self.is_keyword("ORDER"):
            self.take()
            self.expect_keyword("BY")
            self.order_list()
        if self.is_keyword("LIMIT"):
            self.take()
            self.limit = self.integer()
        if self.is_keyword("OFFSET"):
            self.before_offset = self.tokens[self.pos - 1].end
            self.offset = self.take()
            self.integer()
        if self.peek() is not None:
            raise self.fail()
        return _Parsed(
            self.tables,
            self.events,
            self.condition_literals,
            self.limit,
            self.offset,
            self.before_offset,
            self.tokens[-1],
        )

    def integer(self) -> Token:
        token = self.peek()
        if token is None or token.kind != "number" or not token.text.isdigit():
            raise self.fail()
        return self.take()

    def select_list(self) -> None:
        while True:
            if self.is_symbol("*"):
                self.take()
                self.events.append(("wildcard",))
            else:
                self.expression()
                alias = self.maybe_alias()
                if alias is not None:
                    self.aliases.add(alias)
            if not self.is_symbol(","):
                return
            self.take()

    def from_list(self) -> None:
        self.table_ref()
        while True:
            if self.is_symbol(","):
                self.take()
                self.table_ref()
            elif self.is_keyword(*JOIN_STARTS):
                self.join_kind()
                self.table_ref()
                if self.is_keyword("ON"):
                    self.take()
                    self.condition()
            else:
                return

    def join_kind(self) -> None:
        if self.is_keyword("JOIN"):
            self.take()
            return
        word = self.take().text
        if word in ("LEFT", "RIGHT", "FULL") and self.is_keyword("OUTER"):
            self.take()
        self.expect_keyword("JOIN")

    def table_ref(self) -> None:
        table = self.expect_identifier().text.lower()
        alias = self.maybe_alias()
        self.tables.append((alias if alias is not None else table, table))

    def order_list(self) -> None:
        while True:
            first = self.pos
            events_before = len(self.events)
            self.expression()
            single = self.pos - first == 1 and self.tokens[first].kind == "identifier"
            if single and self.tokens[first].text.lower() in self.aliases:
                del self.events[events_before:]
            if self.is_keyword("ASC", "DESC"):
                self.take()
            if not self.is_symbol(","):
                return
            self.take()

    def expression_list(self) -> None:
        self.expression()
        while self.is_symbol(","):
            self.take()
            self.expression()

    def condition(self) -> None:
        outer = self.in_condition
        self.in_condition = True
        self.expression()
        self.in_condition = outer

    # --- expressions, loosest binding first
    def expression(self) -> None:
        self.and_expression()
        while self.is_keyword("OR"):
            self.take()
            self.and_expression()

    def and_expression(self) -> None:
        self.not_expression()
        while self.is_keyword("AND"):
            self.take()
            self.not_expression()

    def not_expression(self) -> None:
        if self.is_keyword("NOT"):
            self.take()
            self.not_expression()
        else:
            self.predicate()

    def predicate(self) -> None:
        self.additive()
        if self.is_symbol(*COMPARISONS):
            self.take()
            self.additive()
        elif self.is_keyword("IS"):
            self.take()
            if self.is_keyword("NOT"):
                self.take()
            self.expect_keyword("NULL")
        else:
            if self.is_keyword("NOT"):
                self.take()
                if not self.is_keyword("LIKE", "IN", "BETWEEN"):
                    raise self.fail()
            self.postfix_predicate()

    def postfix_predicate(self) -> None:
        if self.is_keyword("LIKE"):
            self.take()
            self.additive()
        elif self.is_keyword("IN"):
            self.take()
            self.expect_symbol("(")
            self.expression_list()
            self.expect_symbol(")")
        elif self.is_keyword("BETWEEN"):
            self.take()
            self.additive()
            self.expect_keyword("AND")
            self.additive()

    def additive(self) -> None:
        self.multiplicative()
        while self.is_symbol("+", "-", "||"):
            self.take()
            self.multiplicative()

    def multiplicative(self) -> None:
        self.unary()
        while self.is_symbol("*", "/", "%"):
            self.take()
            self.unary()

    def unary(self) -> None:
        if self.is_symbol("-", "+"):
            self.take()
            self.unary()
        else:
            self.primary()

    def primary(self) -> None:
        token = self.peek()
        if token is None:
            raise self.fail()
        if token.kind in ("number", "string"):
            self.take()
            if self.in_condition:
                self.condition_literals.append(token.text)
        elif token.kind == "placeholder" or (
            token.kind == "keyword" and token.text in ("TRUE", "FALSE", "NULL")
        ):
            self.take()
        elif token.kind == "symbol" and token.text == "(":
            self.take()
            self.expression()
            self.expect_symbol(")")
        elif token.kind == "identifier":
            following = self.peek(1)
            if following is not None and following.kind == "symbol" and following.text == "(":
                self.function_call()
            else:
                self.column()
        else:
            raise self.fail()

    def column(self) -> None:
        first = self.take().text.lower()
        if self.is_symbol("."):
            self.take()
            self.events.append(("column", first, self.expect_identifier().text.lower()))
        else:
            self.events.append(("column", None, first))

    def function_call(self) -> None:
        name = self.take().text.lower()
        self.events.append(("function", name))
        self.take()
        if name in AGGREGATES:
            self.aggregate_arguments(name)
        else:
            self.any_arguments()
        self.expect_symbol(")")

    def aggregate_arguments(self, name: str) -> None:
        if self.is_symbol("*"):
            if name != "count":
                raise self.fail()
            self.take()
            return
        if self.is_symbol(")"):
            raise self.fail()
        if self.is_keyword("DISTINCT"):
            self.take()
        self.expression()

    def any_arguments(self) -> None:
        if self.is_symbol("*"):
            self.take()
        elif not self.is_symbol(")"):
            if self.is_keyword("DISTINCT"):
                self.take()
            self.expression_list()


def _parse_single(sql: str) -> _Parsed | None:
    """The parse of `sql` when it is exactly one statement that fits the subset."""
    tokens, error = lex(sql)
    statements = _statements(tokens)
    if error or len(statements) != 1:
        return None
    try:
        return _Parser(statements[0]).parse()
    except _Syntax:
        return None


class SqlGuard:
    def __init__(self) -> None:
        self._allowed: dict[str, set[str]] = {}

    # --- level 1
    def tokenize(self, sql: str) -> list[list[str]]:
        tokens, error = lex(sql)
        rows = [[token.kind, token.text] for token in tokens]
        if error:
            rows.append(["error", error])
        return rows

    def check(self, sql: str) -> list[list[str]]:
        tokens, error = lex(sql)
        if error:
            return [["lex-error", error]]
        count = len(_statements(tokens))
        if count == 0:
            return [["empty", ""]]
        if count > 1:
            return [["multiple-statements", str(count)]]
        return []

    # --- level 2
    def check_read_only(self, sql: str) -> list[list[str]]:
        rows = self.check(sql)
        if rows and rows[0][0] in ("lex-error", "empty"):
            return rows
        tokens, _ = lex(sql)
        for statement in _statements(tokens):
            first = statement[0]
            if not (first.kind == "keyword" and first.text == "SELECT"):
                rows.append(["not-select", first.text])
        for token in tokens:
            if token.kind == "keyword" and token.text in FORBIDDEN_KEYWORDS:
                rows.append(["forbidden-keyword", token.text])
        if any(t.kind == "comment" and t.text.startswith("/*!") for t in tokens):
            rows.append(["executable-comment", ""])
        return _distinct(rows)

    def naive_check(self, sql: str) -> str:
        lowered = sql.lower()
        return "reject" if any(word in lowered for word in NAIVE_WORDS) else "allow"

    def contrast(self, sql: str) -> str:
        naive = self.naive_check(sql)
        guard = "reject" if self.check_read_only(sql) else "allow"
        if naive == guard:
            return "agree"
        return "false-alarm" if naive == "reject" else "miss"

    # --- level 3
    def allow_table(self, table: str, columns: list[str]) -> bool:
        name = table.lower()
        if name in self._allowed:
            return False
        self._allowed[name] = {column.lower() for column in columns}
        return True

    def check_access(self, sql: str) -> list[list[str]]:
        rows = self.check_read_only(sql)
        if rows:
            return rows
        tokens, _ = lex(sql)
        try:
            parsed = _Parser(_statements(tokens)[0]).parse()
        except _Syntax as problem:
            return [["syntax", problem.text]]
        return _distinct(self._access_rows(parsed))

    def _access_rows(self, parsed: _Parsed) -> list[list[str]]:
        rows: list[list[str]] = []
        names: list[str] = []
        for source, table in parsed.tables:
            if table not in self._allowed:
                rows.append(["table-not-allowed", table])
            if source in names:
                rows.append(["duplicate-source", source])
            names.append(source)
        for event in parsed.events:
            rows.extend(self._event_rows(event, parsed.tables))
        return rows

    def _event_rows(self, event: tuple, sources: list[tuple[str, str]]) -> list[list[str]]:
        if event[0] == "wildcard":
            return [["wildcard-not-allowed", "*"]]
        if event[0] == "function":
            return [] if event[1] in AGGREGATES else [["function-not-allowed", event[1]]]
        _, qualifier, name = event
        if qualifier is not None:
            return self._qualified_rows(qualifier, name, sources)
        return self._unqualified_rows(name, sources)

    def _qualified_rows(
        self, qualifier: str, name: str, sources: list[tuple[str, str]]
    ) -> list[list[str]]:
        table = next((t for s, t in sources if s == qualifier), None)
        if table is None:
            return [["unknown-source", qualifier]]
        if table in self._allowed and name not in self._allowed[table]:
            return [["column-not-allowed", f"{qualifier}.{name}"]]
        return []

    def _unqualified_rows(self, name: str, sources: list[tuple[str, str]]) -> list[list[str]]:
        holders = sum(1 for _, t in sources if t in self._allowed and name in self._allowed[t])
        if holders > 1:
            return [["ambiguous-column", name]]
        if holders == 0 and all(t in self._allowed for _, t in sources):
            return [["column-not-allowed", name]]
        return []

    # --- level 4
    def limited_sql(self, sql: str, max_rows: int) -> str:
        if self.check_access(sql):
            return ""
        parsed = _parse_single(sql)
        assert parsed is not None
        if parsed.limit is not None:
            if int(parsed.limit.text) > max_rows:
                return sql[: parsed.limit.start] + str(max_rows) + sql[parsed.limit.end :]
            return sql
        if parsed.offset is not None:
            before = parsed.before_offset
        else:
            before = parsed.last.end
        return sql[:before] + f" LIMIT {max_rows}" + sql[before:]

    def parameter_findings(self, sql: str, user_values: list[str]) -> list[list[str]]:
        parsed = _parse_single(sql)
        if parsed is None:
            return []
        rows = [
            ["inlined-value" if text in user_values else "literal", text]
            for text in parsed.condition_literals
        ]
        return _distinct(rows)
