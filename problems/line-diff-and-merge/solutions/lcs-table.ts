const KEEP = " ";
const REMOVE = "-";
const ADD = "+";
const HEADER = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@$/;
const MARKERS = ["<<<<<<< ours", "||||||| base", "=======", ">>>>>>> theirs"] as const;

type Step = { kind: string; line: string };
type Hunk = { start: number; old: string[]; fresh: string[] };

function sameLines(first: string[], second: string[]): boolean {
  return first.length === second.length && first.every((line, index) => line === second[index]);
}

export class LineDiff {
  private last: string[] = [];

  // Level 1
  lcs(before: string[], after: string[]): string[] {
    return script(before, after)
      .filter((step) => step.kind === KEEP)
      .map((step) => step.line);
  }

  diff(before: string[], after: string[]): string[] {
    return script(before, after).map((step) => step.kind + step.line);
  }

  // Level 2
  unified(before: string[], after: string[], context: number): string[] {
    const steps = script(before, after);
    const changed: number[] = [];
    steps.forEach((step, index) => {
      if (step.kind !== KEEP) {
        changed.push(index);
      }
    });
    if (changed.length === 0) {
      return [];
    }
    const groups: Array<[number, number]> = [];
    let first = changed[0];
    let previous = changed[0];
    for (const index of changed.slice(1)) {
      if (index - previous - 1 > 2 * context) {
        groups.push([first, previous]);
        first = index;
      }
      previous = index;
    }
    groups.push([first, previous]);
    const lines: string[] = [];
    for (const [groupFirst, groupLast] of groups) {
      const start = Math.max(0, groupFirst - context);
      const end = Math.min(steps.length, groupLast + context + 1);
      const prior = steps.slice(0, start);
      const hunk = steps.slice(start, end);
      const oldRange = range(count(prior, ADD), count(hunk, ADD));
      const newRange = range(count(prior, REMOVE), count(hunk, REMOVE));
      lines.push(`@@ -${oldRange} +${newRange} @@`);
      for (const step of hunk) {
        lines.push(step.kind + step.line);
      }
    }
    return lines;
  }

  // Level 3
  applyPatch(lines: string[], patch: string[], maxOffset: number): string[] {
    const result = [...lines];
    const statuses: string[] = [];
    let added = 0;
    let shift = 0;
    let floor = 0;
    for (const hunk of parseHunks(patch)) {
      const base = hunk.start + added;
      const found = findHunk(result, hunk.old, base + shift, floor, maxOffset);
      if (found === -1) {
        statuses.push("rejected");
        continue;
      }
      result.splice(found, hunk.old.length, ...hunk.fresh);
      shift = found - base;
      added += hunk.fresh.length - hunk.old.length;
      floor = found + hunk.fresh.length;
      statuses.push(`applied ${shift}`);
    }
    this.last = result;
    return statuses;
  }

  patched(): string[] {
    return [...this.last];
  }

  // Level 4
  merge(base: string[], ours: string[], theirs: string[]): string[] {
    const toOurs = keptAt(base, ours);
    const toTheirs = keptAt(base, theirs);
    const merged: string[] = [];
    let o = 0;
    let a = 0;
    let b = 0;
    base.forEach((line, index) => {
      const j = toOurs.get(index);
      const k = toTheirs.get(index);
      if (j !== undefined && k !== undefined) {
        merged.push(...resolve(base.slice(o, index), ours.slice(a, j), theirs.slice(b, k)));
        merged.push(line);
        o = index + 1;
        a = j + 1;
        b = k + 1;
      }
    });
    merged.push(...resolve(base.slice(o), ours.slice(a), theirs.slice(b)));
    return merged;
  }
}

// The diff with the most kept lines that, read from the top, keeps rather than removes and
// removes rather than adds wherever both stay optimal.
function script(before: string[], after: string[]): Step[] {
  const n = before.length;
  const m = after.length;
  // longest[i][j]: the length of a longest common subsequence of before[i:] and after[j:].
  const longest: Int32Array[] = Array.from({ length: n + 1 }, () => new Int32Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      longest[i][j] =
        before[i] === after[j]
          ? longest[i + 1][j + 1] + 1
          : Math.max(longest[i + 1][j], longest[i][j + 1]);
    }
  }
  const steps: Step[] = [];
  let i = 0;
  let j = 0;
  while (i < n || j < m) {
    if (i < n && j < m && before[i] === after[j]) {
      steps.push({ kind: KEEP, line: before[i] });
      i++;
      j++;
    } else if (i < n && (j === m || longest[i + 1][j] >= longest[i][j + 1])) {
      steps.push({ kind: REMOVE, line: before[i] });
      i++;
    } else {
      steps.push({ kind: ADD, line: after[j] });
      j++;
    }
  }
  return steps;
}

// The number of steps that are not of the given kind.
function count(steps: Step[], skipped: string): number {
  return steps.filter((step) => step.kind !== skipped).length;
}

function range(linesBefore: number, size: number): string {
  if (size === 0) {
    return `${linesBefore},0`;
  }
  return size === 1 ? `${linesBefore + 1}` : `${linesBefore + 1},${size}`;
}

// Each hunk with the index where its old lines start, its old lines and its new lines.
function parseHunks(patch: string[]): Hunk[] {
  const hunks: Hunk[] = [];
  for (const line of patch) {
    const header = HEADER.exec(line);
    if (header !== null) {
      const oldStart = Number(header[1]);
      const oldCount = header[2] === undefined ? 1 : Number(header[2]);
      hunks.push({ start: oldCount > 0 ? oldStart - 1 : oldStart, old: [], fresh: [] });
      continue;
    }
    const hunk = hunks[hunks.length - 1];
    const text = line.slice(1);
    if (line.startsWith(KEEP)) {
      hunk.old.push(text);
      hunk.fresh.push(text);
    } else if (line.startsWith(REMOVE)) {
      hunk.old.push(text);
    } else if (line.startsWith(ADD)) {
      hunk.fresh.push(text);
    }
  }
  return hunks;
}

// The nearest position to `expected` where `old` matches, the earlier one first, or -1.
function findHunk(result: string[], old: string[], expected: number, floor: number, maxOffset: number): number {
  for (let distance = 0; distance <= maxOffset; distance++) {
    for (const position of [expected - distance, expected + distance]) {
      const fits = floor <= position && position + old.length <= result.length;
      if (fits && sameLines(result.slice(position, position + old.length), old)) {
        return position;
      }
    }
  }
  return -1;
}

// For each line of `base` that the diff to `other` keeps, the index it keeps it at.
function keptAt(base: string[], other: string[]): Map<number, number> {
  const kept = new Map<number, number>();
  let i = 0;
  let j = 0;
  for (const step of script(base, other)) {
    if (step.kind === KEEP) {
      kept.set(i, j);
    }
    if (step.kind !== ADD) {
      i++;
    }
    if (step.kind !== REMOVE) {
      j++;
    }
  }
  return kept;
}

function resolve(base: string[], ours: string[], theirs: string[]): string[] {
  if (sameLines(ours, theirs)) {
    return ours;
  }
  if (sameLines(ours, base)) {
    return theirs;
  }
  if (sameLines(theirs, base)) {
    return ours;
  }
  const [start, middle, separator, end] = MARKERS;
  return [start, ...ours, middle, ...base, separator, ...theirs, end];
}
