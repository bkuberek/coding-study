// Versions are parsed once into numbers and identifiers; ranges are expanded into comparator sets.
// Resolving is a depth-first search that picks the smallest open package name and tries its
// versions from the highest down, undoing a choice when the rest cannot be resolved. Explaining a
// failure reruns the search with constraints left out, one at a time.

interface Version {
  major: number;
  minor: number;
  patch: number;
  pre: string[];
}

type Comparator = [string, Version];
type ComparatorSets = Comparator[][];

interface Dependency {
  name: string;
  text: string;
  sets: ComparatorSets;
  edge: number;
}

interface Release {
  name: string;
  text: string;
  version: Version;
  dependencies: Dependency[];
}

interface Root {
  name: string;
  text: string;
  sets: ComparatorSets;
}

const NUMBER = /^(0|[1-9][0-9]*)$/;
const IDENTIFIER = /^[0-9A-Za-z-]+$/;
const DIGITS = /^[0-9]+$/;
const WILDCARDS = new Set(["x", "X", "*"]);
const OPERATORS = [">=", "<=", ">", "<", "=", "^", "~"];

function parse(text: string): Version | null {
  const plus = text.indexOf("+");
  const rest = plus >= 0 ? text.slice(0, plus) : text;
  if (plus >= 0 && !text.slice(plus + 1).split(".").every((part) => IDENTIFIER.test(part))) {
    return null;
  }
  const dash = rest.indexOf("-");
  const numbers = (dash >= 0 ? rest.slice(0, dash) : rest).split(".");
  if (numbers.length !== 3 || !numbers.every((n) => NUMBER.test(n))) return null;
  const pre = dash >= 0 ? rest.slice(dash + 1).split(".") : [];
  for (const part of pre) {
    if (!IDENTIFIER.test(part) || (DIGITS.test(part) && !NUMBER.test(part))) return null;
  }
  return { major: Number(numbers[0]), minor: Number(numbers[1]), patch: Number(numbers[2]), pre };
}

function sign(value: number): number {
  return value < 0 ? -1 : value > 0 ? 1 : 0;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareIdentifiers(a: string, b: string): number {
  const aNumeric = DIGITS.test(a);
  const bNumeric = DIGITS.test(b);
  if (aNumeric && bNumeric) return sign(Number(a) - Number(b));
  if (aNumeric !== bNumeric) return aNumeric ? -1 : 1;
  return compareText(a, b);
}

function order(a: Version, b: Version): number {
  if (a.major !== b.major) return sign(a.major - b.major);
  if (a.minor !== b.minor) return sign(a.minor - b.minor);
  if (a.patch !== b.patch) return sign(a.patch - b.patch);
  // A release (no pre-release) sorts after every pre-release of its core.
  if (a.pre.length === 0 || b.pre.length === 0) return sign(b.pre.length - a.pre.length);
  for (let i = 0; i < Math.min(a.pre.length, b.pre.length); i++) {
    const found = compareIdentifiers(a.pre[i], b.pre[i]);
    if (found !== 0) return found;
  }
  return sign(a.pre.length - b.pre.length);
}

function writeVersion(version: Version): string {
  const core = `${version.major}.${version.minor}.${version.patch}`;
  return version.pre.length > 0 ? `${core}-${version.pre.join(".")}` : core;
}

function below(major: number, minor: number, patch: number): Comparator {
  return ["<", { major, minor, patch, pre: ["0"] }];
}

function floorOf(numbers: number[]): Version {
  return { major: numbers[0] ?? 0, minor: numbers[1] ?? 0, patch: numbers[2] ?? 0, pre: [] };
}

// The leading numbers of a pattern such as `1`, `1.x` or `1.2.*`, or null.
function partial(pattern: string): number[] | null {
  const parts = pattern.split(".");
  if (parts.length > 3) return null;
  const numbers: number[] = [];
  for (let i = 0; i < parts.length; i++) {
    if (WILDCARDS.has(parts[i])) {
      return parts.slice(i).every((rest) => WILDCARDS.has(rest)) ? numbers : null;
    }
    if (!NUMBER.test(parts[i])) return null;
    numbers.push(Number(parts[i]));
  }
  return numbers.length < 3 ? numbers : null;
}

function wildcardRange(numbers: number[]): Comparator[] {
  if (numbers.length === 0) return [[">=", floorOf([])]];
  if (numbers.length === 1) return [[">=", floorOf(numbers)], below(numbers[0] + 1, 0, 0)];
  return [[">=", floorOf(numbers)], below(numbers[0], numbers[1] + 1, 0)];
}

function caretUpper(numbers: number[]): Comparator {
  const [major, minor, patch] = [numbers[0] ?? 0, numbers[1] ?? 0, numbers[2] ?? 0];
  if (major > 0 || numbers.length === 1) return below(major + 1, 0, 0);
  if (minor > 0 || numbers.length === 2) return below(0, minor + 1, 0);
  return below(0, 0, patch + 1);
}

function expandTerm(term: string): Comparator[] | null {
  const operator = OPERATORS.find((op) => term.startsWith(op)) ?? "";
  const pattern = term.slice(operator.length);
  const full = parse(pattern);
  if (full !== null) {
    if (operator === "" || operator === "=") return [["=", full]];
    if (operator === "~") return [[">=", full], below(full.major, full.minor + 1, 0)];
    if (operator === "^") return [[">=", full], caretUpper([full.major, full.minor, full.patch])];
    return [[operator, full]];
  }
  const numbers = partial(pattern);
  if (numbers === null || !["", "=", "^", "~"].includes(operator)) return null;
  if (operator === "^" && numbers.length > 0) return [[">=", floorOf(numbers)], caretUpper(numbers)];
  return wildcardRange(numbers);
}

function expand(text: string): ComparatorSets | null {
  const sets: ComparatorSets = [];
  for (const piece of text.split("||")) {
    const terms = piece.split(" ").filter((term) => term !== "");
    if (terms.length === 0) return null;
    const comparators: Comparator[] = [];
    for (const term of terms) {
      const expanded = expandTerm(term);
      if (expanded === null) return null;
      comparators.push(...expanded);
    }
    sets.push(comparators);
  }
  return sets;
}

function holds(version: Version, [operator, bound]: Comparator): boolean {
  const found = order(version, bound);
  switch (operator) {
    case "=":
      return found === 0;
    case ">":
      return found > 0;
    case ">=":
      return found >= 0;
    case "<":
      return found < 0;
    default:
      return found <= 0;
  }
}

function inSet(version: Version, comparators: Comparator[]): boolean {
  if (!comparators.every((comparator) => holds(version, comparator))) return false;
  if (version.pre.length === 0) return true;
  return comparators.some(
    ([, bound]) =>
      bound.pre.length > 0 &&
      bound.major === version.major &&
      bound.minor === version.minor &&
      bound.patch === version.patch,
  );
}

function inRange(version: Version, sets: ComparatorSets): boolean {
  return sets.some((comparators) => inSet(version, comparators));
}

export class SemverResolver {
  private releases = new Map<string, Release[]>();
  private published: Release[] = [];
  private edges = 0;

  // Level 1
  isValid(version: string): boolean {
    return parse(version) !== null;
  }

  compare(first: string, second: string): number {
    return order(parse(first)!, parse(second)!);
  }

  sortVersions(versions: string[]): string[] {
    const valid: [Version, string][] = [];
    for (const text of versions) {
      const parsed = parse(text);
      if (parsed !== null) valid.push([parsed, text]);
    }
    valid.sort(([a, x], [b, y]) => order(a, b) || compareText(x, y));
    return valid.map(([, text]) => text);
  }

  changeKind(before: string, after: string): string {
    const old = parse(before);
    const now = parse(after);
    if (old === null || now === null) return "invalid";
    const found = order(now, old);
    if (found < 0) return "downgrade";
    if (found === 0) return "none";
    if (now.major !== old.major) return "major";
    if (now.minor !== old.minor) return "minor";
    if (now.patch !== old.patch) return "patch";
    return "pre-release";
  }

  // Level 2
  expandRange(versionRange: string): string[] {
    const sets = expand(versionRange);
    if (sets === null) return [];
    return sets.map((comparators) => comparators.map(([op, bound]) => op + writeVersion(bound)).join(" "));
  }

  satisfies(version: string, versionRange: string): boolean {
    const parsed = parse(version);
    const sets = expand(versionRange);
    return parsed !== null && sets !== null && inRange(parsed, sets);
  }

  maxSatisfying(versions: string[], versionRange: string): string {
    const sets = expand(versionRange);
    if (sets === null) return "";
    let best: [Version, string] | null = null;
    for (const text of versions) {
      const parsed = parse(text);
      if (parsed === null || !inRange(parsed, sets)) continue;
      if (best === null || (order(parsed, best[0]) || compareText(text, best[1])) > 0) best = [parsed, text];
    }
    return best === null ? "" : best[1];
  }

  // Level 3
  publish(name: string, version: string, dependencies: string[][]): string {
    const parsed = parse(version);
    if (parsed === null) return "invalid-version";
    const releases = this.releases.get(name) ?? [];
    if (releases.some((release) => order(release.version, parsed) === 0)) return "duplicate";
    const names = dependencies.map(([dep]) => dep);
    const expanded = dependencies.map(([, text]) => expand(text));
    if (new Set(names).size !== names.length || names.includes(name) || expanded.includes(null)) {
      return "invalid-dependency";
    }
    const release: Release = { name, text: version, version: parsed, dependencies: [] };
    dependencies.forEach(([dep, text], i) => {
      release.dependencies.push({ name: dep, text, sets: expanded[i]!, edge: this.edges++ });
    });
    releases.push(release);
    releases.sort((a, b) => order(b.version, a.version));
    this.releases.set(name, releases);
    this.published.push(release);
    return "ok";
  }

  candidates(name: string, versionRange: string): string[] {
    const sets = expand(versionRange);
    if (sets === null) return [];
    return (this.releases.get(name) ?? []).filter((r) => inRange(r.version, sets)).map((r) => r.text);
  }

  resolve(requirements: string[][]): string[] {
    return this.result(this.search(this.roots(requirements), new Set(), new Set(), new Map()));
  }

  // Level 4
  explain(requirements: string[][]): string[] {
    const roots = this.roots(requirements);
    if (this.search(roots, new Set(), new Set(), new Map()) !== null) return [];
    const lines: [boolean, number, string][] = roots.map((root, i) => [
      true,
      i,
      `root requires ${root.name} ${root.text}`,
    ]);
    for (const release of this.published) {
      for (const dependency of release.dependencies) {
        lines.push([false, dependency.edge, `${release.name}@${release.text} requires ${dependency.name} ${dependency.text}`]);
      }
    }
    const droppedRoots = new Set<number>();
    const droppedEdges = new Set<number>();
    const kept: string[] = [];
    for (const [isRoot, number, line] of lines) {
      const dropped = isRoot ? droppedRoots : droppedEdges;
      dropped.add(number);
      if (this.search(roots, droppedRoots, droppedEdges, new Map()) !== null) {
        dropped.delete(number);
        kept.push(line);
      }
    }
    return kept;
  }

  lockedResolve(requirements: string[][], lock: string[]): string[] {
    return this.result(this.search(this.roots(requirements), new Set(), new Set(), this.lockOf(lock)));
  }

  update(requirements: string[][], lock: string[], unlock: string[]): string[] {
    const before = this.lockOf(lock);
    const preferred = new Map([...before].filter(([name]) => !unlock.includes(name)));
    const chosen = this.search(this.roots(requirements), new Set(), new Set(), preferred);
    if (chosen === null) return ["unsatisfiable"];
    const names = [...new Set([...before.keys(), ...chosen.keys()])].sort(compareText);
    const changes: string[] = [];
    for (const name of names) {
      const old = before.get(name);
      const now = chosen.get(name)?.text;
      if (old === undefined) changes.push(`${name}: added ${now}`);
      else if (now === undefined) changes.push(`${name}: removed ${old}`);
      else if (old !== now) changes.push(`${name}: ${old} -> ${now} (${this.changeKind(old, now)})`);
    }
    return changes;
  }

  // Helpers
  private roots(requirements: string[][]): Root[] {
    return requirements.map(([name, text]) => ({ name, text, sets: expand(text)! }));
  }

  private lockOf(lock: string[]): Map<string, string> {
    const found = new Map<string, string>();
    for (const entry of lock) {
      const at = entry.indexOf("@");
      found.set(entry.slice(0, at), entry.slice(at + 1));
    }
    return found;
  }

  private result(chosen: Map<string, Release> | null): string[] {
    if (chosen === null) return [];
    return [...chosen.keys()].sort(compareText).map((name) => `${name}@${chosen.get(name)!.text}`);
  }

  // The chosen release of every needed package, or null when the constraints in force cannot
  // all hold.
  private search(
    roots: Root[],
    droppedRoots: Set<number>,
    droppedEdges: Set<number>,
    preferred: Map<string, string>,
  ): Map<string, Release> | null {
    const rootRanges = roots.filter((_, i) => !droppedRoots.has(i));
    const chosen = new Map<string, Release>();
    const inForce = (release: Release) => release.dependencies.filter((d) => !droppedEdges.has(d.edge));

    const solve = (): boolean => {
      const needed = new Set(rootRanges.map((root) => root.name));
      for (const release of chosen.values()) {
        for (const dependency of inForce(release)) needed.add(dependency.name);
      }
      const open = [...needed].filter((name) => !chosen.has(name)).sort(compareText);
      if (open.length === 0) return true;
      const name = open[0];
      const ranges = rootRanges.filter((root) => root.name === name).map((root) => root.sets);
      for (const release of chosen.values()) {
        for (const dependency of inForce(release)) {
          if (dependency.name === name) ranges.push(dependency.sets);
        }
      }
      const releases = this.releases.get(name) ?? [];
      const wanted = preferred.get(name);
      const tries = [
        ...releases.filter((r) => r.text === wanted),
        ...releases.filter((r) => r.text !== wanted),
      ];
      for (const release of tries) {
        if (!ranges.every((sets) => inRange(release.version, sets))) continue;
        const clash = inForce(release).some((dependency) => {
          const other = chosen.get(dependency.name);
          return other !== undefined && !inRange(other.version, dependency.sets);
        });
        if (clash) continue;
        chosen.set(name, release);
        if (solve()) return true;
        chosen.delete(name);
      }
      return false;
    };

    return solve() ? new Map(chosen) : null;
  }
}
