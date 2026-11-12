interface SchemaRow {
  name: string;
  kind: string;
  required: boolean;
}

interface Run {
  cases: Map<string, { input: string; output: string }>;
  criteria: string[];
  judge: Map<string, Map<string, number>>;
  human: Map<string, Map<string, number>>;
}

const WORD = /[a-z0-9]+/g;

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function sortedText(values: Iterable<string>): string[] {
  return [...values].sort(compareText);
}

/** Integer division rounded toward negative infinity, exact for the sizes of this problem. */
function floorDiv(numerator: number, denominator: number): number {
  const remainder = ((numerator % denominator) + denominator) % denominator;
  return (numerator - remainder) / denominator;
}

/** The mean of whole scores in hundredths, ties rounded up. */
function halfUpMean(total: number, count: number): number {
  return floorDiv(200 * total + count, 2 * count);
}

function floorPercent(part: number, whole: number): number {
  return whole > 0 ? floorDiv(100 * part, whole) : 0;
}

function parseJson(text: string): { ok: boolean; value: unknown } {
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch {
    return { ok: false, value: null };
  }
}

function matchesType(value: unknown, kind: string): boolean {
  if (kind === "string") {
    return typeof value === "string";
  }
  if (kind === "bool") {
    return typeof value === "boolean";
  }
  if (kind === "int") {
    return typeof value === "number" && Number.isInteger(value);
  }
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function kappaThousandths(pairs: [boolean, boolean][]): string {
  const both = pairs.filter(([judge, human]) => judge && human).length;
  const judgeOnly = pairs.filter(([judge, human]) => judge && !human).length;
  const humanOnly = pairs.filter(([judge, human]) => human && !judge).length;
  const neither = pairs.length - both - judgeOnly - humanOnly;
  const count = pairs.length;
  const chance = (both + judgeOnly) * (both + humanOnly) + (humanOnly + neither) * (judgeOnly + neither);
  const numerator = count * (both + neither) - chance;
  const denominator = count * count - chance;
  if (denominator === 0) {
    return "undefined";
  }
  const scaled = floorDiv(2000 * Math.abs(numerator) + denominator, 2 * denominator);
  return String(numerator < 0 ? -scaled : scaled);
}

export class ReleaseGate {
  private schema: SchemaRow[] = [];
  private banned: string[] = [];
  private readonly runs = new Map<string, Run>();
  private critical: string[] = [];
  private maxDrop = 0;

  // Level 1
  setSchema(rows: string[][]): void {
    this.schema = rows.map(([name, kind, requirement]) => ({ name, kind, required: requirement === "required" }));
  }

  setBannedWords(words: string[]): void {
    this.banned = [...words];
  }

  check(output: string): string[] {
    const codes: string[] = [];
    const { ok, value } = parseJson(output);
    if (!ok) {
      codes.push("json");
    } else if (typeof value !== "object" || value === null || Array.isArray(value)) {
      codes.push("object");
    } else {
      const object = value as Record<string, unknown>;
      for (const { name, kind, required } of this.schema) {
        if (!Object.prototype.hasOwnProperty.call(object, name)) {
          if (required) {
            codes.push(`missing:${name}`);
          }
        } else if (!matchesType(object[name], kind)) {
          codes.push(`type:${name}`);
        }
      }
    }
    const present = new Set(output.toLowerCase().match(WORD) ?? []);
    for (const word of sortedText(new Set(this.banned))) {
      if (present.has(word)) {
        codes.push(`banned:${word}`);
      }
    }
    return codes;
  }

  addRun(run: string, caseIds: string[], inputs: string[], outputs: string[]): number {
    const table: Run = { cases: new Map(), criteria: [], judge: new Map(), human: new Map() };
    caseIds.forEach((caseId, index) => {
      table.cases.set(caseId, { input: inputs[index], output: outputs[index] });
    });
    this.runs.set(run, table);
    return table.cases.size;
  }

  checkRun(run: string): string[][] {
    const table = this.runs.get(run);
    if (table === undefined) {
      return [];
    }
    return sortedText(table.cases.keys()).map((caseId) => {
      const codes = this.check((table.cases.get(caseId) as { output: string }).output);
      return [caseId, codes.length > 0 ? "fail" : "pass", ...codes];
    });
  }

  // Level 2
  addScores(run: string, criteria: string[], caseIds: string[], scores: number[][]): number {
    const table = this.table(run);
    table.criteria = [...criteria];
    table.judge = new Map(
      caseIds.map((caseId, row) => [caseId, new Map(criteria.map((criterion, column) => [criterion, scores[row][column]]))]),
    );
    return caseIds.length;
  }

  addHumanScores(run: string, caseIds: string[], criteria: string[], scores: number[][]): number {
    const table = this.table(run);
    let cells = 0;
    caseIds.forEach((caseId, row) => {
      const cellsOfCase = table.human.get(caseId) ?? new Map<string, number>();
      criteria.forEach((criterion, column) => {
        cellsOfCase.set(criterion, scores[row][column]);
        cells += 1;
      });
      table.human.set(caseId, cellsOfCase);
    });
    return cells;
  }

  aggregate(run: string): string[][] {
    const table = this.runs.get(run);
    if (table === undefined || table.judge.size === 0) {
      return [];
    }
    const rows: string[][] = [];
    let grandTotal = 0;
    let grandCount = 0;
    let grandHuman = 0;
    for (const criterion of sortedText(table.criteria)) {
      const scores = [...table.judge.keys()].map((caseId) => this.effective(table, caseId, criterion));
      const total = scores.reduce((sum, score) => sum + score, 0);
      const human = [...table.judge.keys()].filter((caseId) => table.human.get(caseId)?.has(criterion)).length;
      rows.push([criterion, String(halfUpMean(total, scores.length)), String(human)]);
      grandTotal += total;
      grandCount += scores.length;
      grandHuman += human;
    }
    rows.push(["overall", String(halfUpMean(grandTotal, grandCount)), String(grandHuman)]);
    return rows;
  }

  agreement(run: string, passScore: number): string[][] {
    const table = this.runs.get(run);
    if (table === undefined) {
      return [];
    }
    const rows: string[][] = [];
    for (const criterion of sortedText(table.criteria)) {
      const pairs = this.verdictPairs(table, criterion, passScore);
      if (pairs.length === 0) {
        continue;
      }
      const agreed = pairs.filter(([judge, human]) => judge === human).length;
      rows.push([criterion, String(pairs.length), String(floorPercent(agreed, pairs.length)), kappaThousandths(pairs)]);
    }
    return rows;
  }

  disagreements(run: string, passScore: number): string[][] {
    const table = this.runs.get(run);
    if (table === undefined) {
      return [];
    }
    const rows: string[][] = [];
    for (const caseId of sortedText(table.human.keys())) {
      const cells = table.human.get(caseId) as Map<string, number>;
      for (const criterion of sortedText(cells.keys())) {
        const judge = (table.judge.get(caseId) as Map<string, number>).get(criterion) as number;
        const human = cells.get(criterion) as number;
        if (judge >= passScore !== human >= passScore) {
          rows.push([caseId, criterion, String(judge), String(human)]);
        }
      }
    }
    return rows;
  }

  // Level 3
  compare(baselineRuns: string[], candidateRuns: string[], passScore: number): string[][] {
    return this.golden(baselineRuns).map((caseId) => this.compareRow(caseId, baselineRuns, candidateRuns, passScore));
  }

  summarize(baselineRuns: string[], candidateRuns: string[], passScore: number): number[] {
    const rows = this.compare(baselineRuns, candidateRuns, passScore);
    const count = (column: number, text: string): number => rows.filter((row) => row[column] === text).length;
    return [
      count(1, "regression"),
      count(1, "improvement"),
      count(1, "same"),
      count(2, "pass->fail"),
      count(2, "fail->pass"),
    ];
  }

  // Level 4
  configureGate(critical: string[], maxDrop: number): void {
    this.critical = [...critical];
    this.maxDrop = maxDrop;
  }

  gate(baselineRuns: string[], candidateRuns: string[], passScore: number): string[][] {
    const reasons = this.assertionReasons(candidateRuns);
    const golden = this.golden(baselineRuns);
    const rows = new Map(this.compare(baselineRuns, candidateRuns, passScore).map((row) => [row[0], row]));
    for (const caseId of sortedText(this.critical)) {
      const row = rows.get(caseId);
      if (row !== undefined && (row[1] === "regression" || row[2] === "pass->fail")) {
        reasons.push(["reason", "critical", caseId, row[1], row[2]]);
      }
    }
    const before = this.quality(baselineRuns, golden);
    const after = this.quality(candidateRuns, golden);
    if (before - after > this.maxDrop) {
      reasons.push(["reason", "quality", String(before), String(after), String(before - after), String(this.maxDrop)]);
    }
    const decision = reasons.length > 0 ? "block" : "ship";
    return [["decision", decision], ...reasons, ...this.proposals(golden, candidateRuns, passScore)];
  }

  // Helpers
  private table(run: string): Run {
    return this.runs.get(run) as Run;
  }

  private effective(table: Run, caseId: string, criterion: string): number {
    const human = table.human.get(caseId)?.get(criterion);
    return human !== undefined ? human : ((table.judge.get(caseId) as Map<string, number>).get(criterion) as number);
  }

  private verdictPairs(table: Run, criterion: string, passScore: number): [boolean, boolean][] {
    const pairs: [boolean, boolean][] = [];
    for (const caseId of sortedText(table.human.keys())) {
      const human = table.human.get(caseId)?.get(criterion);
      if (human !== undefined) {
        const judge = (table.judge.get(caseId) as Map<string, number>).get(criterion) as number;
        pairs.push([judge >= passScore, human >= passScore]);
      }
    }
    return pairs;
  }

  private golden(baselineRuns: string[]): string[] {
    return sortedText(this.table(baselineRuns[0]).cases.keys());
  }

  private caseScore(run: string, caseId: string): number {
    const table = this.table(run);
    return table.criteria.reduce((sum, criterion) => sum + this.effective(table, caseId, criterion), 0);
  }

  private failureCodes(run: string, caseId: string, passScore: number): string[] {
    const table = this.table(run);
    const codes = this.check((table.cases.get(caseId) as { output: string }).output);
    if (table.judge.has(caseId)) {
      for (const criterion of sortedText(table.criteria)) {
        if (this.effective(table, caseId, criterion) < passScore) {
          codes.push(`low:${criterion}`);
        }
      }
    }
    return codes;
  }

  private majorityPasses(runs: string[], caseId: string, passScore: number): { passes: boolean; count: number } {
    const count = runs.filter((run) => this.failureCodes(run, caseId, passScore).length === 0).length;
    return { passes: 2 * count > runs.length, count };
  }

  private compareRow(caseId: string, baselineRuns: string[], candidateRuns: string[], passScore: number): string[] {
    const before = baselineRuns.map((run) => this.caseScore(run, caseId));
    const after = candidateRuns.map((run) => this.caseScore(run, caseId));
    let change = "same";
    if (Math.max(...after) < Math.min(...before)) {
      change = "regression";
    } else if (Math.min(...after) > Math.max(...before)) {
      change = "improvement";
    }
    const was = this.majorityPasses(baselineRuns, caseId, passScore);
    const now = this.majorityPasses(candidateRuns, caseId, passScore);
    let flip = "-";
    if (was.passes && !now.passes) {
      flip = "pass->fail";
    } else if (now.passes && !was.passes) {
      flip = "fail->pass";
    }
    return [
      caseId,
      change,
      flip,
      String(Math.min(...before)),
      String(Math.max(...before)),
      String(Math.min(...after)),
      String(Math.max(...after)),
      `${was.count}/${baselineRuns.length}`,
      `${now.count}/${candidateRuns.length}`,
    ];
  }

  private quality(runs: string[], golden: string[]): number {
    let total = 0;
    let count = 0;
    for (const run of runs) {
      const table = this.table(run);
      for (const caseId of golden) {
        for (const criterion of table.criteria) {
          total += this.effective(table, caseId, criterion);
          count += 1;
        }
      }
    }
    return halfUpMean(total, count);
  }

  private assertionReasons(candidateRuns: string[]): string[][] {
    const reasons: string[][] = [];
    for (const run of candidateRuns) {
      const table = this.table(run);
      for (const caseId of sortedText(table.cases.keys())) {
        const codes = this.check((table.cases.get(caseId) as { output: string }).output);
        if (codes.length > 0) {
          reasons.push(["reason", "assertion", run, caseId, codes.join(",")]);
        }
      }
    }
    return reasons;
  }

  private proposals(golden: string[], candidateRuns: string[], passScore: number): string[][] {
    const known = new Set(golden);
    const fresh = new Set<string>();
    for (const run of candidateRuns) {
      for (const caseId of this.table(run).cases.keys()) {
        if (!known.has(caseId)) {
          fresh.add(caseId);
        }
      }
    }
    const proposals: string[][] = [];
    for (const caseId of sortedText(fresh)) {
      const codes = new Set<string>();
      for (const run of candidateRuns) {
        if (this.table(run).cases.has(caseId)) {
          for (const code of this.failureCodes(run, caseId, passScore)) {
            codes.add(code);
          }
        }
      }
      if (codes.size > 0) {
        const first = candidateRuns.find((run) => this.table(run).cases.has(caseId)) as string;
        const input = (this.table(first).cases.get(caseId) as { input: string }).input;
        proposals.push(["propose", caseId, input, sortedText(codes).join(",")]);
      }
    }
    return proposals;
  }
}
