// Parses a small SQL subset, checks it against the catalog, and plans it: written order with
// filters pushed to the scans, row estimates from table statistics, the cheapest left-deep join
// order by dynamic programming over subsets of tables, then access paths and join methods.

const KEYWORDS = new Set(["SELECT", "FROM", "JOIN", "ON", "WHERE", "AND"]);
const SYMBOLS = "*,.=<>";
const RANDOM_READ = 4;

type Column = [string, string];
type Condition = { column: Column; op: string; value: string };
type Edge = { left: number; right: number; leftColumn: Column; rightColumn: Column };

class QueryError extends Error {}

const isLetter = (c: string) => (c >= "a" && c <= "z") || (c >= "A" && c <= "Z") || c === "_";
const isDigit = (c: string) => c >= "0" && c <= "9";

function tokenize(sql: string): string[] {
  const tokens: string[] = [];
  let i = 0;
  while (i < sql.length) {
    const c = sql[i];
    if (c === " ") {
      i++;
    } else if (isLetter(c)) {
      let j = i + 1;
      while (j < sql.length && (isLetter(sql[j]) || isDigit(sql[j]))) j++;
      tokens.push(sql.slice(i, j));
      i = j;
    } else if (isDigit(c) || (c === "-" && i + 1 < sql.length && isDigit(sql[i + 1]))) {
      let j = i + 1;
      while (j < sql.length && isDigit(sql[j])) j++;
      tokens.push(sql.slice(i, j));
      i = j;
    } else if (SYMBOLS.includes(c)) {
      tokens.push(c);
      i++;
    } else {
      throw new QueryError("syntax");
    }
  }
  return tokens;
}

// SELECT ... FROM t [JOIN u ON a.x = b.y]... [WHERE c op n [AND ...]], as written.
class Query {
  columns: Column[] | null = null;
  tables: string[] = [];
  joins: [string, Column, Column][] = [];
  conditions: Condition[] = [];
  private tokens: string[];
  private pos = 0;

  constructor(sql: string) {
    this.tokens = tokenize(sql);
    this.expect("SELECT");
    if (this.peek() === "*") {
      this.pos++;
    } else {
      this.columns = [this.column()];
      while (this.peek() === ",") {
        this.pos++;
        this.columns.push(this.column());
      }
    }
    this.expect("FROM");
    this.tables.push(this.name());
    while (this.peek() === "JOIN") {
      this.pos++;
      const table = this.name();
      this.tables.push(table);
      this.expect("ON");
      const left = this.column();
      this.expect("=");
      this.joins.push([table, left, this.column()]);
    }
    if (this.peek() === "WHERE") {
      this.pos++;
      this.conditions.push(this.condition());
      while (this.peek() === "AND") {
        this.pos++;
        this.conditions.push(this.condition());
      }
    }
    if (this.pos !== this.tokens.length) throw new QueryError("syntax");
  }

  private peek(): string {
    return this.pos < this.tokens.length ? this.tokens[this.pos] : "";
  }

  private expect(token: string): void {
    if (this.peek() !== token) throw new QueryError("syntax");
    this.pos++;
  }

  private name(): string {
    const token = this.peek();
    if (token === "" || !isLetter(token[0]) || KEYWORDS.has(token)) throw new QueryError("syntax");
    this.pos++;
    return token;
  }

  private column(): Column {
    const table = this.name();
    this.expect(".");
    return [table, this.name()];
  }

  private condition(): Condition {
    const column = this.column();
    const op = this.peek();
    if (op !== "=" && op !== "<" && op !== ">") throw new QueryError("syntax");
    this.pos++;
    const value = this.peek();
    if (value === "" || !(isDigit(value[0]) || value[0] === "-")) throw new QueryError("syntax");
    this.pos++;
    return { column, op, value };
  }

  columnRefs(): Column[] {
    const refs = [...(this.columns ?? [])];
    for (const [, left, right] of this.joins) refs.push(left, right);
    for (const condition of this.conditions) refs.push(condition.column);
    return refs;
  }
}

const dotted = (column: Column) => `${column[0]}.${column[1]}`;
const showCondition = (c: Condition) => `${dotted(c.column)} ${c.op} ${c.value}`;

// Exact whole-number division: a % b and (a - a % b) / b are exact below 2^53.
const divide = (a: number, b: number) => (a - (a % b)) / b;

// numerator / denominator rounded half up, and at least 1.
const rounded = (numerator: number, denominator: number) =>
  Math.max(1, divide(2 * numerator + denominator, 2 * denominator));

// One checked query: tables in written order (a table is its position, a set of tables a bit
// mask), the conditions of each table, and one edge per join, written with the earlier table first.
class Plan {
  private planner: QueryPlanner;
  private query: Query;
  private tables: string[];
  private where: Condition[][];
  private edges: Edge[] = [];

  constructor(planner: QueryPlanner, sql: string, needStats: boolean) {
    const query = new Query(sql);
    const seen = new Set<string>();
    for (const table of query.tables) {
      if (!planner.columns.has(table)) throw new QueryError(`unknown-table ${table}`);
      if (seen.has(table)) throw new QueryError(`duplicate-table ${table}`);
      seen.add(table);
    }
    for (const [table, column] of query.columnRefs()) {
      if (!seen.has(table) || !planner.columns.get(table)!.includes(column)) {
        throw new QueryError(`unknown-column ${table}.${column}`);
      }
    }
    query.joins.forEach(([table, first, second], index) => {
      const earlier = query.tables.slice(0, index + 1);
      let [left, right] = [first, second];
      if (left[0] === table && earlier.includes(right[0])) [left, right] = [right, left];
      else if (!(right[0] === table && earlier.includes(left[0]))) {
        throw new QueryError(`bad-join ${table}`);
      }
      const position = (name: string) => query.tables.indexOf(name);
      this.edges.push({ left: position(left[0]), right: index + 1, leftColumn: left, rightColumn: right });
    });
    if (needStats) {
      for (const table of query.tables) {
        if (!planner.stats.has(table)) throw new QueryError(`no-stats ${table}`);
      }
    }
    this.planner = planner;
    this.query = query;
    this.tables = query.tables;
    this.where = this.tables.map((t) => query.conditions.filter((c) => c.column[0] === t));
  }

  private head(): string {
    const columns = this.query.columns;
    return "project " + (columns === null ? "*" : columns.map(dotted).join(", "));
  }

  // --- estimates
  private distinct(column: Column): number {
    const [, counts] = this.planner.stats.get(column[0])!;
    return counts[this.planner.columns.get(column[0])!.indexOf(column[1])];
  }

  private divisor(condition: Condition): number {
    return condition.op === "=" ? this.distinct(condition.column) : 3;
  }

  private base(table: number): number {
    return this.planner.stats.get(this.tables[table])![0];
  }

  // The rows of a table after its conditions.
  private out(table: number): number {
    if (this.where[table].length === 0) return this.base(table);
    let divisor = 1;
    for (const condition of this.where[table]) divisor *= this.divisor(condition);
    return rounded(this.base(table), divisor);
  }

  private rows(mask: number): number {
    let numerator = 1;
    for (let t = 0; t < this.tables.length; t++) if (mask & (1 << t)) numerator *= this.out(t);
    let denominator = 1;
    for (const edge of this.edges) {
      if (mask & (1 << edge.left) && mask & (1 << edge.right)) {
        denominator *= Math.max(this.distinct(edge.leftColumn), this.distinct(edge.rightColumn));
      }
    }
    return rounded(numerator, denominator);
  }

  // The edge between a table and a set it joins, written with the set's column first.
  private edgeInto(mask: number, table: number): [Column, Column] | null {
    for (const edge of this.edges) {
      if (edge.right === table && mask & (1 << edge.left)) return [edge.leftColumn, edge.rightColumn];
      if (edge.left === table && mask & (1 << edge.right)) return [edge.rightColumn, edge.leftColumn];
    }
    return null;
  }

  // --- level 4 access paths and join methods
  // The cheapest way to read a table: its cost, and the position of the condition an index
  // serves, or -1 for a full scan. Ties keep the full scan, then the condition written first.
  private access(table: number): [number, number] {
    let best: [number, number] = [this.base(table), -1];
    const indexed = this.planner.indexes.get(this.tables[table]) ?? new Set<string>();
    this.where[table].forEach((condition, position) => {
      if (condition.op === "=" && indexed.has(condition.column[1])) {
        const cost = RANDOM_READ * rounded(this.base(table), this.distinct(condition.column));
        if (cost < best[0]) best = [cost, position];
      }
    });
    return best;
  }

  private joinStep(leftRows: number, table: number): [string, number] {
    const innerCost = this.access(table)[0];
    const nested = leftRows * innerCost;
    const hashed = innerCost + this.out(table) + leftRows;
    return nested <= hashed ? ["nested loop", nested] : ["hash join", hashed];
  }

  // --- printing
  private tableLines(table: number, depth: number, mode: number): string[] {
    const pad = "  ".repeat(depth);
    const name = this.tables[table];
    let conditions = this.where[table];
    let scan: string;
    if (mode === 1) {
      scan = `scan ${name}`;
    } else if (mode < 4) {
      scan = `scan ${name} (rows=${this.base(table)})`;
    } else {
      const [cost, used] = this.access(table);
      if (used < 0) {
        scan = `full scan ${name} (rows=${this.base(table)} cost=${cost})`;
      } else {
        const matched = rounded(this.base(table), this.distinct(conditions[used].column));
        scan = `index scan ${showCondition(conditions[used])} (rows=${matched} cost=${cost})`;
        conditions = conditions.filter((_, position) => position !== used);
      }
    }
    if (conditions.length === 0) return [pad + scan];
    let shown = "filter " + conditions.map(showCondition).join(" AND ");
    if (mode > 1) shown += ` (rows=${this.out(table)})`;
    return [pad + shown, pad + "  " + scan];
  }

  // The plan joining the tables in this order, left-deep, under its project line. Mode 1 prints
  // no numbers, 2 the rows, 3 the rows and the cost, 4 the access paths and the join methods.
  lines(order: number[], mode: number): string[] {
    const depth = order.length;
    const steps: string[] = [];
    let joined = 1 << order[0];
    let cost = mode === 4 ? this.access(order[0])[0] : 0;
    for (const table of order.slice(1)) {
      const [leftColumn, rightColumn] = this.edgeInto(joined, table)!;
      let name = "join";
      if (mode === 4) {
        const [method, step] = this.joinStep(this.rows(joined), table);
        name = method;
        cost += step;
      }
      joined |= 1 << table;
      if (mode === 3) cost += this.rows(joined);
      let text = `${name} ${dotted(leftColumn)} = ${dotted(rightColumn)}`;
      if (mode === 2) text += ` (rows=${this.rows(joined)})`;
      else if (mode > 2) text += ` (rows=${this.rows(joined)} cost=${cost})`;
      steps.push(text);
    }
    // Pre-order: the last join on top, each join's left input below it, then the first table;
    // the table joined at step k is the right input of that join, at depth n - k + 1.
    const result = [this.head()];
    steps.reverse().forEach((text, level) => result.push("  ".repeat(level + 1) + text));
    result.push(...this.tableLines(order[0], depth, mode));
    order.slice(1).forEach((table, k) => result.push(...this.tableLines(table, depth - k, mode)));
    return result;
  }

  writtenOrder(): number[] {
    return this.tables.map((_, index) => index);
  }

  private before(a: [number, number[]], b: [number, number[]]): boolean {
    if (a[0] !== b[0]) return a[0] < b[0];
    for (let i = 0; i < a[1].length; i++) {
      const x = this.tables[a[1][i]];
      const y = this.tables[b[1][i]];
      if (x !== y) return x < y;
    }
    return false;
  }

  // Dynamic programming over subsets: the cheapest left-deep order of every connected set, built
  // from the cheapest order of the set without its last table. Ties go to the order whose list of
  // table names comes first.
  bestOrder(mode: number): number[] {
    const count = this.tables.length;
    const best = new Map<number, [number, number[]]>();
    for (let t = 0; t < count; t++) best.set(1 << t, [mode === 4 ? this.access(t)[0] : 0, [t]]);
    for (let size = 2; size <= count; size++) {
      for (const [mask, [cost, order]] of [...best.entries()]) {
        if (order.length !== size - 1) continue;
        for (let t = 0; t < count; t++) {
          if (mask & (1 << t) || this.edgeInto(mask, t) === null) continue;
          const grown = mask | (1 << t);
          const step = mode === 4 ? this.joinStep(this.rows(mask), t)[1] : this.rows(grown);
          const candidate: [number, number[]] = [cost + step, [...order, t]];
          const current = best.get(grown);
          if (current === undefined || this.before(candidate, current)) best.set(grown, candidate);
        }
      }
    }
    return best.get((1 << count) - 1)![1];
  }
}

export class QueryPlanner {
  columns = new Map<string, string[]>();
  stats = new Map<string, [number, number[]]>();
  indexes = new Map<string, Set<string>>();

  private plan(sql: string, needStats: boolean, mode: number): string[] {
    try {
      const plan = new Plan(this, sql, needStats);
      return plan.lines(mode >= 3 ? plan.bestOrder(mode) : plan.writtenOrder(), mode);
    } catch (error) {
      if (error instanceof QueryError) return [`error: ${error.message}`];
      throw error;
    }
  }

  // Level 1
  addTable(table: string, columns: string[]): string {
    if (this.columns.has(table)) return "duplicate";
    this.columns.set(table, [...columns]);
    return "ok";
  }

  logicalPlan(sql: string): string[] {
    return this.plan(sql, false, 1);
  }

  // Level 2
  analyze(table: string, rows: number, distinct: number[]): string {
    const columns = this.columns.get(table);
    if (columns === undefined) return "unknown-table";
    if (distinct.length !== columns.length || rows < 1 || distinct.some((c) => c < 1 || c > rows)) {
      return "bad-stats";
    }
    this.stats.set(table, [rows, [...distinct]]);
    return "ok";
  }

  estimate(sql: string): string[] {
    return this.plan(sql, true, 2);
  }

  // Level 3
  optimize(sql: string): string[] {
    return this.plan(sql, true, 3);
  }

  // Level 4
  addIndex(table: string, column: string): string {
    const columns = this.columns.get(table);
    if (columns === undefined) return "unknown-table";
    if (!columns.includes(column)) return "unknown-column";
    const indexed = this.indexes.get(table) ?? new Set<string>();
    if (indexed.has(column)) return "duplicate";
    indexed.add(column);
    this.indexes.set(table, indexed);
    return "ok";
  }

  explain(sql: string): string[] {
    return this.plan(sql, true, 4);
  }
}
