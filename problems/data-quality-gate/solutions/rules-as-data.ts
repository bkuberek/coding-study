const ROW_CHECKS = new Set(["not-null", "type", "allowed", "range", "unique", "references"]);
const BATCH_CHECKS = new Set(["row-count", "drift", "freshness"]);
const ACTIONS = new Set(["warn", "quarantine", "block"]);
const EMPTY_SHARE = 0.0001;
const DAYS_IN_MONTH = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

function allDigits(text: string): boolean {
  for (const ch of text) {
    if (ch < "0" || ch > "9") {
      return false;
    }
  }
  return true;
}

function isInt(text: string): boolean {
  const digits = text.startsWith("-") ? text.slice(1) : text;
  return digits.length >= 1 && digits.length <= 15 && allDigits(digits);
}

function isDate(text: string): boolean {
  if (text.length !== 10 || text[4] !== "-" || text[7] !== "-") {
    return false;
  }
  const parts = [text.slice(0, 4), text.slice(5, 7), text.slice(8, 10)];
  if (!parts.every(allDigits)) {
    return false;
  }
  const [year, month, day] = parts.map(Number);
  if (year < 1 || month < 1 || month > 12) {
    return false;
  }
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const last = month === 2 && leap ? 29 : DAYS_IN_MONTH[month - 1];
  return day >= 1 && day <= last;
}

// A non-negative decimal with at most four places, in units of 0.0001.
function tenThousandths(decimal: string): number {
  const [whole, fraction = ""] = decimal.split(".");
  return Number(whole) * 10000 + Number((fraction + "0000").slice(0, 4));
}

interface Rule {
  ruleId: string;
  check: string;
  columns: string[];
  params: string[];
  action: string;
}

// Rules are data: each one is a check name, its columns and its parameters, kept in the order they
// were added. Validation runs every rule over the rows and reports what failed; the gate runs the
// row rules first, sets aside the rows that quarantine rules reject, and runs the batch rules on
// what is left.
export class QualityGate {
  private index = new Map<string, number>();
  private rules: Rule[] = [];
  private byId = new Map<string, Rule>();
  private dimensions = new Map<string, Set<string>>();
  private previous: string[][] | null = null;
  private now = 0;
  private aside: number[] = [];

  constructor(columns: string[]) {
    columns.forEach((name, at) => this.index.set(name, at));
  }

  // Level 1
  addRule(ruleId: string, check: string, columns: string[], params: string[]): boolean {
    const known = ROW_CHECKS.has(check) || BATCH_CHECKS.has(check);
    if (this.byId.has(ruleId) || !known || columns.some((column) => !this.index.has(column))) {
      return false;
    }
    if (check === "references" && !this.dimensions.has(params[0])) {
      return false;
    }
    const rule: Rule = { ruleId, check, columns: [...columns], params: [...params], action: "block" };
    this.rules.push(rule);
    this.byId.set(ruleId, rule);
    return true;
  }

  validate(rows: string[][]): string[][] {
    return this.rules.flatMap((rule) => this.findings(rule, rows));
  }

  failingRows(rows: string[][], ruleId: string): number[] {
    const rule = this.byId.get(ruleId);
    if (rule === undefined || BATCH_CHECKS.has(rule.check)) {
      return [];
    }
    const failing = new Set<number>();
    for (const [, bad] of this.rowFailures(rule, rows)) {
      bad.forEach((at) => failing.add(at));
    }
    return [...failing].sort((a, b) => a - b);
  }

  // Level 2
  loadDimension(name: string, keys: string[]): number {
    this.dimensions.set(name, new Set(keys));
    return (this.dimensions.get(name) as Set<string>).size;
  }

  setPreviousBatch(rows: string[][]): number {
    this.previous = rows.map((row) => [...row]);
    return rows.length;
  }

  // Level 3
  setTime(now: number): void {
    this.now = now;
  }

  // Level 4
  setAction(ruleId: string, action: string): boolean {
    const rule = this.byId.get(ruleId);
    if (rule === undefined || !ACTIONS.has(action)) {
      return false;
    }
    if (action === "quarantine" && BATCH_CHECKS.has(rule.check)) {
      return false;
    }
    rule.action = action;
    return true;
  }

  decide(rows: string[][]): string[][] {
    const setAside = new Set<number>();
    for (const rule of this.rules) {
      if (ROW_CHECKS.has(rule.check) && rule.action === "quarantine") {
        this.failingRows(rows, rule.ruleId).forEach((at) => setAside.add(at));
      }
    }
    const kept = rows.filter((_, at) => !setAside.has(at));
    const findings: string[][] = [];
    for (const rule of this.rules) {
      const seen = ROW_CHECKS.has(rule.check) ? rows : kept;
      for (const entry of this.findings(rule, seen)) {
        findings.push([...entry, rule.action]);
      }
    }
    if (findings.some((entry) => entry[3] === "block")) {
      this.aside = [];
      return [["block", "0", "0"], ...findings];
    }
    this.aside = [...setAside].sort((a, b) => a - b);
    this.previous = kept;
    return [["publish", String(kept.length), String(setAside.size)], ...findings];
  }

  quarantined(): number[] {
    return [...this.aside];
  }

  // Helpers
  private findings(rule: Rule, rows: string[][]): string[][] {
    if (ROW_CHECKS.has(rule.check)) {
      const found: string[][] = [];
      for (const [column, bad] of this.rowFailures(rule, rows)) {
        if (bad.length > 0) {
          found.push([rule.ruleId, column, String(bad.length)]);
        }
      }
      return found;
    }
    const observed = this.batchFailure(rule, rows);
    return observed === null ? [] : [[rule.ruleId, rule.columns.join(""), observed]];
  }

  // For each column of a row rule (one joined key for unique), the rows that fail it.
  private rowFailures(rule: Rule, rows: string[][]): [string, number[]][] {
    if (rule.check === "unique") {
      const groups = new Map<string, number[]>();
      rows.forEach((row, at) => {
        const parts = rule.columns.map((column) => row[this.index.get(column) as number]);
        if (parts.includes("")) {
          return;
        }
        const key = parts.map((part) => `${part.length}:${part}`).join("");
        const group = groups.get(key);
        if (group === undefined) {
          groups.set(key, [at]);
        } else {
          group.push(at);
        }
      });
      const bad = [...groups.values()].filter((group) => group.length > 1).flat();
      return [[rule.columns.join("+"), bad.sort((a, b) => a - b)]];
    }
    return rule.columns.map((column) => {
      const at = this.index.get(column) as number;
      const bad: number[] = [];
      rows.forEach((row, number) => {
        if (this.fails(rule, row[at])) {
          bad.push(number);
        }
      });
      return [column, bad];
    });
  }

  private fails(rule: Rule, value: string): boolean {
    if (rule.check === "not-null") {
      return value === "";
    }
    if (value === "") {
      return false;
    }
    switch (rule.check) {
      case "type":
        return !(rule.params[0] === "int" ? isInt(value) : isDate(value));
      case "allowed":
        return !rule.params.includes(value);
      case "range":
        return isInt(value) && (Number(value) < Number(rule.params[0]) || Number(value) > Number(rule.params[1]));
      default:
        return !(this.dimensions.get(rule.params[0]) as Set<string>).has(value);
    }
  }

  // The observed value of a failing batch rule, or null when it passes.
  private batchFailure(rule: Rule, rows: string[][]): string | null {
    if (rule.check === "row-count") {
      if (this.previous === null) {
        return null;
      }
      const before = this.previous.length;
      const tolerance = Number(rule.params[0]);
      const low = Math.floor((before * (100 - tolerance)) / 100);
      const high = Math.ceil((before * (100 + tolerance)) / 100);
      return rows.length >= low && rows.length <= high ? null : String(rows.length);
    }
    const column = this.index.get(rule.columns[0]) as number;
    const values = this.integers(rows, column);
    if (rule.check === "freshness") {
      if (values.length === 0) {
        return "none";
      }
      const lag = this.now - Math.max(...values);
      return lag > Number(rule.params[0]) ? String(lag) : null;
    }
    if (this.previous === null) {
      return null;
    }
    const baseline = this.integers(this.previous, column);
    if (values.length === 0 || baseline.length === 0) {
      return null;
    }
    const edges = rule.params.slice(1).map(Number);
    const units = Math.floor(this.psi(values, baseline, edges) * 10000 + 0.5);
    if (units < tenThousandths(rule.params[0])) {
      return null;
    }
    return `${Math.floor(units / 10000)}.${String(units % 10000).padStart(4, "0")}`;
  }

  private integers(rows: string[][], column: number): number[] {
    return rows.filter((row) => isInt(row[column])).map((row) => Number(row[column]));
  }

  private psi(values: number[], baseline: number[], edges: number[]): number {
    const shares = (sample: number[]): number[] => {
      const counts = new Array<number>(edges.length + 1).fill(0);
      for (const value of sample) {
        counts[this.binOf(value, edges)]++;
      }
      return counts.map((count) => (count === 0 ? EMPTY_SHARE : count / sample.length));
    };
    const actual = shares(values);
    const expected = shares(baseline);
    let total = 0;
    for (let bin = 0; bin < actual.length; bin++) {
      total += (actual[bin] - expected[bin]) * Math.log(actual[bin] / expected[bin]);
    }
    return total;
  }

  // The number of edges at or below the value.
  private binOf(value: number, edges: number[]): number {
    let low = 0;
    let high = edges.length;
    while (low < high) {
      const middle = (low + high) >>> 1;
      if (edges[middle] <= value) {
        low = middle + 1;
      } else {
        high = middle;
      }
    }
    return low;
  }
}
