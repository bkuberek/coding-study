const GRAMMAR_KEYWORDS =
  "SELECT FROM WHERE GROUP BY HAVING ORDER LIMIT OFFSET AS JOIN INNER LEFT RIGHT FULL OUTER CROSS ON AND OR NOT NULL IS IN LIKE BETWEEN DISTINCT ASC DESC UNION ALL TRUE FALSE WITH".split(
    " ",
  );
const FORBIDDEN_LIST =
  "INSERT UPDATE DELETE MERGE REPLACE DROP CREATE ALTER TRUNCATE RENAME GRANT REVOKE CALL EXEC EXECUTE COPY ATTACH DETACH PRAGMA VACUUM SET INTO".split(
    " ",
  );
const FORBIDDEN_KEYWORDS = new Set(FORBIDDEN_LIST);
const KEYWORDS = new Set([...GRAMMAR_KEYWORDS, ...FORBIDDEN_LIST]);
const AGGREGATES = new Set(["count", "sum", "avg", "min", "max"]);
const NAIVE_WORDS = ["insert", "update", "delete", "drop", "alter", "create", "truncate"];
const STRING_PREFIXES = "ENXBenxb";
const TWO_CHAR_SYMBOLS = ["<=", ">=", "<>", "!=", "||"];
const ONE_CHAR_SYMBOLS = "(),.*+-/%=<>";
const BLANKS = " \t\n\r";
const COMPARISONS = ["=", "<>", "!=", "<", "<=", ">", ">="];
const JOIN_STARTS = ["INNER", "LEFT", "RIGHT", "FULL", "CROSS", "JOIN"];
const END_OF_INPUT = "end of input";

type Row = string[];

interface Token {
  kind: string;
  text: string;
  start: number;
  end: number;
}

function isDigit(char: string): boolean {
  return char >= "0" && char <= "9" && char.length === 1;
}

function isWordStart(char: string): boolean {
  return (
    char.length === 1 && ((char >= "a" && char <= "z") || (char >= "A" && char <= "Z") || char === "_")
  );
}

function isWordChar(char: string): boolean {
  return isWordStart(char) || isDigit(char);
}

// The decoded content of a quoted piece that opens at `start`, and the index after it.
function scanQuoted(sql: string, start: number, quote: string): [string, number] | null {
  let content = "";
  let i = start + 1;
  while (i < sql.length) {
    if (sql[i] === quote) {
      if (sql[i + 1] === quote) {
        content += quote;
        i += 2;
        continue;
      }
      return [content, i + 1];
    }
    content += sql[i];
    i += 1;
  }
  return null;
}

// The index after the number at `start`: digits, then optionally a point and digits.
function scanNumber(sql: string, start: number): number {
  let i = start;
  while (i < sql.length && isDigit(sql[i])) i += 1;
  if (sql[i] === "." && isDigit(sql[i + 1] ?? "")) {
    i += 1;
    while (i < sql.length && isDigit(sql[i])) i += 1;
  }
  return i;
}

function scanWord(sql: string, start: number): number {
  let i = start;
  while (i < sql.length && isWordChar(sql[i])) i += 1;
  return i;
}

function lex(sql: string): { tokens: Token[]; error: string } {
  const tokens: Token[] = [];
  const n = sql.length;
  const push = (kind: string, text: string, start: number, end: number): void => {
    tokens.push({ kind, text, start, end });
  };
  let i = 0;
  while (i < n) {
    const c = sql[i];
    const next = sql[i + 1] ?? "";
    if (BLANKS.includes(c)) {
      i += 1;
    } else if (c === "-" && next === "-") {
      let j = i;
      while (j < n && sql[j] !== "\n" && sql[j] !== "\r") j += 1;
      push("comment", sql.slice(i, j), i, j);
      i = j;
    } else if (c === "/" && next === "*") {
      const close = sql.indexOf("*/", i + 2);
      if (close < 0) return { tokens, error: "unterminated-comment" };
      push("comment", sql.slice(i, close + 2), i, close + 2);
      i = close + 2;
    } else if (c === "'") {
      const scanned = scanQuoted(sql, i, "'");
      if (scanned === null) return { tokens, error: "unterminated-string" };
      push("string", scanned[0], i, scanned[1]);
      i = scanned[1];
    } else if (c === '"') {
      const scanned = scanQuoted(sql, i, '"');
      if (scanned === null) return { tokens, error: "unterminated-identifier" };
      if (scanned[0] === "") return { tokens, error: "empty-identifier" };
      push("identifier", scanned[0], i, scanned[1]);
      i = scanned[1];
    } else if (isDigit(c) || (c === "." && isDigit(next))) {
      const j = scanNumber(sql, i);
      if (j < n && isWordChar(sql[j])) return { tokens, error: "malformed-number" };
      push("number", sql.slice(i, j), i, j);
      i = j;
    } else if (isWordStart(c)) {
      const j = scanWord(sql, i);
      const word = sql.slice(i, j);
      if (word.length === 1 && STRING_PREFIXES.includes(word) && sql[j] === "'") {
        return { tokens, error: "prefixed-string" };
      }
      if (KEYWORDS.has(word.toUpperCase())) push("keyword", word.toUpperCase(), i, j);
      else push("identifier", word, i, j);
      i = j;
    } else if (c === ";") {
      push("semicolon", ";", i, i + 1);
      i += 1;
    } else if (c === "?") {
      push("placeholder", "?", i, i + 1);
      i += 1;
    } else if (c === "$" && isDigit(next)) {
      let j = i + 1;
      while (j < n && isDigit(sql[j])) j += 1;
      push("placeholder", sql.slice(i, j), i, j);
      i = j;
    } else if (c === ":" && isWordStart(next)) {
      const j = scanWord(sql, i + 1);
      push("placeholder", sql.slice(i, j), i, j);
      i = j;
    } else if (TWO_CHAR_SYMBOLS.includes(sql.slice(i, i + 2))) {
      push("symbol", sql.slice(i, i + 2), i, i + 2);
      i += 2;
    } else if (ONE_CHAR_SYMBOLS.includes(c)) {
      push("symbol", c, i, i + 1);
      i += 1;
    } else {
      return { tokens, error: "unexpected-character" };
    }
  }
  return { tokens, error: "" };
}

// The non-empty statements: the tokens between semicolons, comments left out.
function statementsOf(tokens: Token[]): Token[][] {
  const groups: Token[][] = [[]];
  for (const token of tokens) {
    if (token.kind === "semicolon") groups.push([]);
    else if (token.kind !== "comment") groups[groups.length - 1].push(token);
  }
  return groups.filter((group) => group.length > 0);
}

function distinct(rows: Row[]): Row[] {
  const seen = new Set<string>();
  const kept: Row[] = [];
  for (const row of rows) {
    const key = JSON.stringify(row);
    if (!seen.has(key)) {
      seen.add(key);
      kept.push(row);
    }
  }
  return kept;
}

class Syntax extends Error {
  readonly text: string;
  constructor(text: string) {
    super(text);
    this.text = text;
  }
}

type SqlEvent =
  | { kind: "wildcard" }
  | { kind: "function"; name: string }
  | { kind: "column"; qualifier: string | null; name: string };

interface Parsed {
  tables: [string, string][];
  events: SqlEvent[];
  conditionLiterals: string[];
  limit: Token | null;
  offset: Token | null;
  beforeOffset: number;
  last: Token;
}

class Parser {
  private pos = 0;
  private tables: [string, string][] = [];
  private events: SqlEvent[] = [];
  private aliases = new Set<string>();
  private conditionLiterals: string[] = [];
  private inCondition = false;
  private limit: Token | null = null;
  private offset: Token | null = null;
  private beforeOffset = 0;
  private readonly tokens: Token[];

  constructor(tokens: Token[]) {
    this.tokens = tokens;
  }

  private peek(ahead = 0): Token | undefined {
    return this.tokens[this.pos + ahead];
  }

  private fail(): Syntax {
    return new Syntax(this.peek()?.text ?? END_OF_INPUT);
  }

  private isKeyword(...names: string[]): boolean {
    const token = this.peek();
    return token !== undefined && token.kind === "keyword" && names.includes(token.text);
  }

  private isSymbol(...texts: string[]): boolean {
    const token = this.peek();
    return token !== undefined && token.kind === "symbol" && texts.includes(token.text);
  }

  private take(): Token {
    const token = this.peek();
    if (token === undefined) throw this.fail();
    this.pos += 1;
    return token;
  }

  private expectKeyword(name: string): Token {
    if (!this.isKeyword(name)) throw this.fail();
    return this.take();
  }

  private expectSymbol(text: string): Token {
    if (!this.isSymbol(text)) throw this.fail();
    return this.take();
  }

  private expectIdentifier(): Token {
    const token = this.peek();
    if (token === undefined || token.kind !== "identifier") throw this.fail();
    return this.take();
  }

  private maybeAlias(): string | null {
    if (this.isKeyword("AS")) {
      this.take();
      return this.expectIdentifier().text.toLowerCase();
    }
    const token = this.peek();
    if (token !== undefined && token.kind === "identifier") return this.take().text.toLowerCase();
    return null;
  }

  parse(): Parsed {
    this.expectKeyword("SELECT");
    if (this.isKeyword("DISTINCT")) this.take();
    this.selectList();
    if (this.isKeyword("FROM")) {
      this.take();
      this.fromList();
    }
    if (this.isKeyword("WHERE")) {
      this.take();
      this.condition();
    }
    if (this.isKeyword("GROUP")) {
      this.take();
      this.expectKeyword("BY");
      this.expressionList();
    }
    if (this.isKeyword("HAVING")) {
      this.take();
      this.condition();
    }
    if (this.isKeyword("ORDER")) {
      this.take();
      this.expectKeyword("BY");
      this.orderList();
    }
    if (this.isKeyword("LIMIT")) {
      this.take();
      this.limit = this.integer();
    }
    if (this.isKeyword("OFFSET")) {
      this.beforeOffset = this.tokens[this.pos - 1].end;
      this.offset = this.take();
      this.integer();
    }
    if (this.peek() !== undefined) throw this.fail();
    return {
      tables: this.tables,
      events: this.events,
      conditionLiterals: this.conditionLiterals,
      limit: this.limit,
      offset: this.offset,
      beforeOffset: this.beforeOffset,
      last: this.tokens[this.tokens.length - 1],
    };
  }

  private integer(): Token {
    const token = this.peek();
    if (token === undefined || token.kind !== "number" || !/^[0-9]+$/.test(token.text)) {
      throw this.fail();
    }
    return this.take();
  }

  private selectList(): void {
    for (;;) {
      if (this.isSymbol("*")) {
        this.take();
        this.events.push({ kind: "wildcard" });
      } else {
        this.expression();
        const alias = this.maybeAlias();
        if (alias !== null) this.aliases.add(alias);
      }
      if (!this.isSymbol(",")) return;
      this.take();
    }
  }

  private fromList(): void {
    this.tableRef();
    for (;;) {
      if (this.isSymbol(",")) {
        this.take();
        this.tableRef();
      } else if (this.isKeyword(...JOIN_STARTS)) {
        this.joinKind();
        this.tableRef();
        if (this.isKeyword("ON")) {
          this.take();
          this.condition();
        }
      } else {
        return;
      }
    }
  }

  private joinKind(): void {
    if (this.isKeyword("JOIN")) {
      this.take();
      return;
    }
    const word = this.take().text;
    if ((word === "LEFT" || word === "RIGHT" || word === "FULL") && this.isKeyword("OUTER")) {
      this.take();
    }
    this.expectKeyword("JOIN");
  }

  private tableRef(): void {
    const table = this.expectIdentifier().text.toLowerCase();
    const alias = this.maybeAlias();
    this.tables.push([alias ?? table, table]);
  }

  private orderList(): void {
    for (;;) {
      const first = this.pos;
      const eventsBefore = this.events.length;
      this.expression();
      const single = this.pos - first === 1 && this.tokens[first].kind === "identifier";
      if (single && this.aliases.has(this.tokens[first].text.toLowerCase())) {
        this.events.length = eventsBefore;
      }
      if (this.isKeyword("ASC", "DESC")) this.take();
      if (!this.isSymbol(",")) return;
      this.take();
    }
  }

  private expressionList(): void {
    this.expression();
    while (this.isSymbol(",")) {
      this.take();
      this.expression();
    }
  }

  private condition(): void {
    const outer = this.inCondition;
    this.inCondition = true;
    this.expression();
    this.inCondition = outer;
  }

  private expression(): void {
    this.andExpression();
    while (this.isKeyword("OR")) {
      this.take();
      this.andExpression();
    }
  }

  private andExpression(): void {
    this.notExpression();
    while (this.isKeyword("AND")) {
      this.take();
      this.notExpression();
    }
  }

  private notExpression(): void {
    if (this.isKeyword("NOT")) {
      this.take();
      this.notExpression();
    } else {
      this.predicate();
    }
  }

  private predicate(): void {
    this.additive();
    if (this.isSymbol(...COMPARISONS)) {
      this.take();
      this.additive();
    } else if (this.isKeyword("IS")) {
      this.take();
      if (this.isKeyword("NOT")) this.take();
      this.expectKeyword("NULL");
    } else {
      if (this.isKeyword("NOT")) {
        this.take();
        if (!this.isKeyword("LIKE", "IN", "BETWEEN")) throw this.fail();
      }
      this.postfixPredicate();
    }
  }

  private postfixPredicate(): void {
    if (this.isKeyword("LIKE")) {
      this.take();
      this.additive();
    } else if (this.isKeyword("IN")) {
      this.take();
      this.expectSymbol("(");
      this.expressionList();
      this.expectSymbol(")");
    } else if (this.isKeyword("BETWEEN")) {
      this.take();
      this.additive();
      this.expectKeyword("AND");
      this.additive();
    }
  }

  private additive(): void {
    this.multiplicative();
    while (this.isSymbol("+", "-", "||")) {
      this.take();
      this.multiplicative();
    }
  }

  private multiplicative(): void {
    this.unary();
    while (this.isSymbol("*", "/", "%")) {
      this.take();
      this.unary();
    }
  }

  private unary(): void {
    if (this.isSymbol("-", "+")) {
      this.take();
      this.unary();
    } else {
      this.primary();
    }
  }

  private primary(): void {
    const token = this.peek();
    if (token === undefined) throw this.fail();
    if (token.kind === "number" || token.kind === "string") {
      this.take();
      if (this.inCondition) this.conditionLiterals.push(token.text);
    } else if (
      token.kind === "placeholder" ||
      (token.kind === "keyword" && ["TRUE", "FALSE", "NULL"].includes(token.text))
    ) {
      this.take();
    } else if (token.kind === "symbol" && token.text === "(") {
      this.take();
      this.expression();
      this.expectSymbol(")");
    } else if (token.kind === "identifier") {
      const following = this.peek(1);
      if (following !== undefined && following.kind === "symbol" && following.text === "(") {
        this.functionCall();
      } else {
        this.column();
      }
    } else {
      throw this.fail();
    }
  }

  private column(): void {
    const first = this.take().text.toLowerCase();
    if (this.isSymbol(".")) {
      this.take();
      this.events.push({
        kind: "column",
        qualifier: first,
        name: this.expectIdentifier().text.toLowerCase(),
      });
    } else {
      this.events.push({ kind: "column", qualifier: null, name: first });
    }
  }

  private functionCall(): void {
    const name = this.take().text.toLowerCase();
    this.events.push({ kind: "function", name });
    this.take();
    if (AGGREGATES.has(name)) this.aggregateArguments(name);
    else this.anyArguments();
    this.expectSymbol(")");
  }

  private aggregateArguments(name: string): void {
    if (this.isSymbol("*")) {
      if (name !== "count") throw this.fail();
      this.take();
      return;
    }
    if (this.isSymbol(")")) throw this.fail();
    if (this.isKeyword("DISTINCT")) this.take();
    this.expression();
  }

  private anyArguments(): void {
    if (this.isSymbol("*")) {
      this.take();
    } else if (!this.isSymbol(")")) {
      if (this.isKeyword("DISTINCT")) this.take();
      this.expressionList();
    }
  }
}

// The parse of `sql` when it is exactly one statement that fits the subset.
function parseSingle(sql: string): Parsed | null {
  const { tokens, error } = lex(sql);
  const statements = statementsOf(tokens);
  if (error !== "" || statements.length !== 1) return null;
  try {
    return new Parser(statements[0]).parse();
  } catch (problem) {
    if (problem instanceof Syntax) return null;
    throw problem;
  }
}

export class SqlGuard {
  private allowed = new Map<string, Set<string>>();

  tokenize(sql: string): string[][] {
    const { tokens, error } = lex(sql);
    const rows = tokens.map((token) => [token.kind, token.text]);
    if (error !== "") rows.push(["error", error]);
    return rows;
  }

  check(sql: string): string[][] {
    const { tokens, error } = lex(sql);
    if (error !== "") return [["lex-error", error]];
    const count = statementsOf(tokens).length;
    if (count === 0) return [["empty", ""]];
    if (count > 1) return [["multiple-statements", String(count)]];
    return [];
  }

  checkReadOnly(sql: string): string[][] {
    const rows = this.check(sql);
    if (rows.length > 0 && (rows[0][0] === "lex-error" || rows[0][0] === "empty")) return rows;
    const { tokens } = lex(sql);
    for (const statement of statementsOf(tokens)) {
      const first = statement[0];
      if (!(first.kind === "keyword" && first.text === "SELECT")) {
        rows.push(["not-select", first.text]);
      }
    }
    for (const token of tokens) {
      if (token.kind === "keyword" && FORBIDDEN_KEYWORDS.has(token.text)) {
        rows.push(["forbidden-keyword", token.text]);
      }
    }
    if (tokens.some((t) => t.kind === "comment" && t.text.startsWith("/*!"))) {
      rows.push(["executable-comment", ""]);
    }
    return distinct(rows);
  }

  naiveCheck(sql: string): string {
    const lowered = sql.toLowerCase();
    return NAIVE_WORDS.some((word) => lowered.includes(word)) ? "reject" : "allow";
  }

  contrast(sql: string): string {
    const naive = this.naiveCheck(sql);
    const guard = this.checkReadOnly(sql).length > 0 ? "reject" : "allow";
    if (naive === guard) return "agree";
    return naive === "reject" ? "false-alarm" : "miss";
  }

  allowTable(table: string, columns: string[]): boolean {
    const name = table.toLowerCase();
    if (this.allowed.has(name)) return false;
    this.allowed.set(name, new Set(columns.map((column) => column.toLowerCase())));
    return true;
  }

  checkAccess(sql: string): string[][] {
    const rows = this.checkReadOnly(sql);
    if (rows.length > 0) return rows;
    const { tokens } = lex(sql);
    try {
      return distinct(this.accessRows(new Parser(statementsOf(tokens)[0]).parse()));
    } catch (problem) {
      if (problem instanceof Syntax) return [["syntax", problem.text]];
      throw problem;
    }
  }

  private accessRows(parsed: Parsed): string[][] {
    const rows: string[][] = [];
    const names: string[] = [];
    for (const [source, table] of parsed.tables) {
      if (!this.allowed.has(table)) rows.push(["table-not-allowed", table]);
      if (names.includes(source)) rows.push(["duplicate-source", source]);
      names.push(source);
    }
    for (const event of parsed.events) rows.push(...this.eventRows(event, parsed.tables));
    return rows;
  }

  private eventRows(event: SqlEvent, sources: [string, string][]): string[][] {
    if (event.kind === "wildcard") return [["wildcard-not-allowed", "*"]];
    if (event.kind === "function") {
      return AGGREGATES.has(event.name) ? [] : [["function-not-allowed", event.name]];
    }
    if (event.qualifier !== null) return this.qualifiedRows(event.qualifier, event.name, sources);
    return this.unqualifiedRows(event.name, sources);
  }

  private qualifiedRows(qualifier: string, name: string, sources: [string, string][]): string[][] {
    const found = sources.find(([source]) => source === qualifier);
    if (found === undefined) return [["unknown-source", qualifier]];
    const columns = this.allowed.get(found[1]);
    if (columns !== undefined && !columns.has(name)) {
      return [["column-not-allowed", `${qualifier}.${name}`]];
    }
    return [];
  }

  private unqualifiedRows(name: string, sources: [string, string][]): string[][] {
    const holders = sources.filter(([, table]) => this.allowed.get(table)?.has(name)).length;
    if (holders > 1) return [["ambiguous-column", name]];
    if (holders === 0 && sources.every(([, table]) => this.allowed.has(table))) {
      return [["column-not-allowed", name]];
    }
    return [];
  }

  limitedSql(sql: string, maxRows: number): string {
    if (this.checkAccess(sql).length > 0) return "";
    const parsed = parseSingle(sql);
    if (parsed === null) throw new Error("unreachable: the statement parsed in checkAccess");
    if (parsed.limit !== null) {
      if (BigInt(parsed.limit.text) > BigInt(maxRows)) {
        return sql.slice(0, parsed.limit.start) + String(maxRows) + sql.slice(parsed.limit.end);
      }
      return sql;
    }
    const at = parsed.offset !== null ? parsed.beforeOffset : parsed.last.end;
    return `${sql.slice(0, at)} LIMIT ${maxRows}${sql.slice(at)}`;
  }

  parameterFindings(sql: string, userValues: string[]): string[][] {
    const parsed = parseSingle(sql);
    if (parsed === null) return [];
    return distinct(
      parsed.conditionLiterals.map((text) => [
        userValues.includes(text) ? "inlined-value" : "literal",
        text,
      ]),
    );
  }
}
