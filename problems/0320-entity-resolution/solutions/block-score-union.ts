const TITLES = new Set(["mr", "mrs", "ms", "miss", "dr", "prof"]);
const NAME_KEY_LENGTH = 3;
const PREFIX_LIMIT = 4;
const PREFIX_SCALE = 0.1;
const JARO_WEIGHT = 0.7;
const JACCARD_WEIGHT = 0.3;
const MATCH_THRESHOLD = 0.75;
const MERGE_FLOOR = 0.65;
const FALSE_MERGE = "false-merge";
const MISSED = "missed";

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

function compareRows(a: string[], b: string[]): number {
  for (let i = 0; i < Math.min(a.length, b.length); i++) {
    const order = compareText(a[i], b[i]);
    if (order !== 0) {
      return order;
    }
  }
  return a.length - b.length;
}

function words(text: string): string[] {
  return text.split(" ").filter((word) => word !== "");
}

function trimSpaces(text: string): string {
  return text.replace(/^ +| +$/g, "");
}

function normalizeName(name: string): string {
  let text = name.toLowerCase();
  const parts = text.split(",");
  if (parts.length === 2) {
    text = parts[1] + " " + parts[0];
  }
  text = text.replace(/'/g, "").replace(/[^a-z0-9 ]/g, " ");
  let tokens = words(text);
  if (tokens.length > 1 && TITLES.has(tokens[0])) {
    tokens = tokens.slice(1);
  }
  return tokens.join(" ");
}

function normalizeEmail(email: string): string {
  return trimSpaces(email).toLowerCase();
}

function jaroWinkler(first: string, second: string): number {
  if (first.length === 0 || second.length === 0) {
    return 0;
  }
  const window = Math.max(0, Math.floor(Math.max(first.length, second.length) / 2) - 1);
  const taken: boolean[] = new Array(second.length).fill(false);
  const fromFirst: string[] = [];
  for (let i = 0; i < first.length; i++) {
    const end = Math.min(second.length, i + window + 1);
    for (let j = Math.max(0, i - window); j < end; j++) {
      if (!taken[j] && second[j] === first[i]) {
        taken[j] = true;
        fromFirst.push(first[i]);
        break;
      }
    }
  }
  const matches = fromFirst.length;
  if (matches === 0) {
    return 0;
  }
  const fromSecond = [...second].filter((_, j) => taken[j]);
  let mismatched = 0;
  for (let k = 0; k < matches; k++) {
    if (fromFirst[k] !== fromSecond[k]) {
      mismatched += 1;
    }
  }
  const transpositions = mismatched / 2;
  const jaro = (matches / first.length + matches / second.length + (matches - transpositions) / matches) / 3;
  let prefix = 0;
  while (prefix < Math.min(PREFIX_LIMIT, first.length, second.length) && first[prefix] === second[prefix]) {
    prefix += 1;
  }
  return jaro + prefix * PREFIX_SCALE * (1 - jaro);
}

function tokenJaccard(first: string, second: string): number {
  const left = new Set(words(first));
  const right = new Set(words(second));
  let shared = 0;
  for (const word of left) {
    if (right.has(word)) {
      shared += 1;
    }
  }
  const union = left.size + right.size - shared;
  return union === 0 ? 0 : shared / union;
}

class StoredRecord {
  readonly name: string;
  readonly email: string;

  constructor(name: string, email: string) {
    this.name = normalizeName(name);
    this.email = normalizeEmail(email);
  }

  blockingKeys(): string[] {
    const keys: string[] = [];
    const tokens = words(this.name);
    if (tokens.length > 0) {
      keys.push("n:" + tokens[tokens.length - 1].slice(0, NAME_KEY_LENGTH));
    }
    if (this.email !== "") {
      keys.push("e:" + this.email);
    }
    return keys;
  }
}

/** Union-find over record ids that also keeps the members of each root. */
class Clusters {
  private readonly parent = new Map<string, string>();
  private readonly members = new Map<string, string[]>();

  constructor(ids: string[]) {
    for (const id of ids) {
      this.parent.set(id, id);
      this.members.set(id, [id]);
    }
  }

  find(item: string): string {
    let root = item;
    while (this.parent.get(root) !== root) {
      root = this.parent.get(root) as string;
    }
    let walk = item;
    while (walk !== root) {
      const next = this.parent.get(walk) as string;
      this.parent.set(walk, root);
      walk = next;
    }
    return root;
  }

  membersOf(root: string): string[] {
    return this.members.get(root) as string[];
  }

  union(first: string, second: string): void {
    let a = this.find(first);
    let b = this.find(second);
    if (this.membersOf(a).length < this.membersOf(b).length) {
      [a, b] = [b, a];
    }
    this.parent.set(b, a);
    this.membersOf(a).push(...this.membersOf(b));
    this.members.delete(b);
  }

  groups(): string[][] {
    return [...this.members.values()].map((group) => [...group].sort(compareText)).sort(compareRows);
  }
}

function pairsOf(groups: string[][]): Set<string> {
  const found = new Set<string>();
  for (const group of groups) {
    const sorted = [...group].sort(compareText);
    for (let i = 0; i < sorted.length; i++) {
      for (let j = i + 1; j < sorted.length; j++) {
        found.add(sorted[i] + "\u0000" + sorted[j]);
      }
    }
  }
  return found;
}

function harmonic(precision: number, recall: number): number {
  const total = precision + recall;
  return total === 0 ? 0 : (2 * precision * recall) / total;
}

function overlapScores(predicted: string[][], gold: string[][]): [number, number] {
  const guess = new Map<string, Set<string>>();
  for (const group of predicted) {
    const set = new Set(group);
    group.forEach((id) => guess.set(id, set));
  }
  const truth = new Map<string, Set<string>>();
  for (const group of gold) {
    const set = new Set(group);
    group.forEach((id) => truth.set(id, set));
  }
  let precision = 0;
  let recall = 0;
  for (const [id, wanted] of truth) {
    const got = guess.get(id) as Set<string>;
    let both = 0;
    for (const other of got) {
      if (wanted.has(other)) {
        both += 1;
      }
    }
    precision += both / got.size;
    recall += both / wanted.size;
  }
  return [precision / truth.size, recall / truth.size];
}

export class EntityResolver {
  private readonly records = new Map<string, StoredRecord>();
  private readonly scores = new Map<string, number>();

  // Level 1
  normalizeName(name: string): string {
    return normalizeName(name);
  }

  normalizeEmail(email: string): string {
    return normalizeEmail(email);
  }

  addRecord(recordId: string, name: string, email: string): boolean {
    if (this.records.has(recordId)) {
      return false;
    }
    this.records.set(recordId, new StoredRecord(name, email));
    return true;
  }

  normalized(recordId: string): string[] {
    const record = this.records.get(recordId);
    return record ? [record.name, record.email] : [];
  }

  exactGroups(): string[][] {
    const groups = new Map<string, string[]>();
    for (const [id, record] of this.records) {
      if (record.name !== "" || record.email !== "") {
        const key = record.name + "\u0000" + record.email;
        groups.set(key, [...(groups.get(key) ?? []), id]);
      }
    }
    return [...groups.values()]
      .filter((ids) => ids.length > 1)
      .map((ids) => ids.sort(compareText))
      .sort(compareRows);
  }

  // Level 2
  blockingKeys(recordId: string): string[] {
    const record = this.records.get(recordId);
    return record ? record.blockingKeys().sort(compareText) : [];
  }

  candidatePairs(): string[][] {
    const blocks = new Map<string, string[]>();
    for (const id of [...this.records.keys()].sort(compareText)) {
      for (const key of (this.records.get(id) as StoredRecord).blockingKeys()) {
        blocks.set(key, [...(blocks.get(key) ?? []), id]);
      }
    }
    const pairs = new Map<string, string[]>();
    for (const ids of blocks.values()) {
      for (let i = 0; i < ids.length; i++) {
        for (let j = i + 1; j < ids.length; j++) {
          pairs.set(ids[i] + "\u0000" + ids[j], [ids[i], ids[j]]);
        }
      }
    }
    return [...pairs.values()].sort(compareRows);
  }

  jaroWinkler(first: string, second: string): number {
    return jaroWinkler(first, second);
  }

  tokenJaccard(first: string, second: string): number {
    return tokenJaccard(first, second);
  }

  similarity(first: string, second: string): number {
    const a = this.records.get(first);
    const b = this.records.get(second);
    if (a === undefined || b === undefined) {
      return 0;
    }
    const [low, high] = compareText(first, second) <= 0 ? [first, second] : [second, first];
    const key = low + "\u0000" + high;
    let score = this.scores.get(key);
    if (score === undefined) {
      score = EntityResolver.score(this.records.get(low) as StoredRecord, this.records.get(high) as StoredRecord);
      this.scores.set(key, score);
    }
    return score;
  }

  isMatch(first: string, second: string): boolean {
    return this.records.has(first) && this.records.has(second) && this.similarity(first, second) >= MATCH_THRESHOLD;
  }

  matches(): string[][] {
    return this.candidatePairs().filter(([first, second]) => this.isMatch(first, second));
  }

  // Level 3
  components(): string[][] {
    const clusters = new Clusters([...this.records.keys()]);
    for (const [first, second] of this.matches()) {
      if (clusters.find(first) !== clusters.find(second)) {
        clusters.union(first, second);
      }
    }
    return clusters.groups();
  }

  clusters(): string[][] {
    const clusters = new Clusters([...this.records.keys()]);
    const edges = this.matches()
      .map((pair) => ({ pair, score: this.similarity(pair[0], pair[1]) }))
      .sort((x, y) => y.score - x.score || compareRows(x.pair, y.pair));
    for (const { pair } of edges) {
      const rootA = clusters.find(pair[0]);
      const rootB = clusters.find(pair[1]);
      if (rootA !== rootB && this.mayMerge(clusters.membersOf(rootA), clusters.membersOf(rootB))) {
        clusters.union(pair[0], pair[1]);
      }
    }
    return clusters.groups();
  }

  canonical(recordId: string): string {
    const group = this.entityOf(recordId);
    if (group.length === 0) {
      return "";
    }
    return group.reduce((best, id) => (this.canonicalBefore(id, best) ? id : best));
  }

  aliases(recordId: string): string[] {
    const group = this.entityOf(recordId);
    if (group.length === 0) {
      return [];
    }
    const keeper = (this.records.get(this.canonical(recordId)) as StoredRecord).name;
    const names = new Set(group.map((id) => (this.records.get(id) as StoredRecord).name));
    names.delete(keeper);
    names.delete("");
    return [...names].sort(compareText);
  }

  // Level 4
  pairwiseScores(predicted: string[][], gold: string[][]): number[] {
    const found = pairsOf(predicted);
    const truth = pairsOf(gold);
    let hits = 0;
    for (const pair of found) {
      if (truth.has(pair)) {
        hits += 1;
      }
    }
    const precision = found.size > 0 ? hits / found.size : 1;
    const recall = truth.size > 0 ? hits / truth.size : 1;
    return [precision, recall, harmonic(precision, recall)];
  }

  bcubedScores(predicted: string[][], gold: string[][]): number[] {
    const [precision, recall] = overlapScores(predicted, gold);
    return [precision, recall, harmonic(precision, recall)];
  }

  pairErrors(predicted: string[][], gold: string[][]): string[][] {
    const found = pairsOf(predicted);
    const truth = pairsOf(gold);
    const rows: string[][] = [];
    for (const pair of found) {
      if (!truth.has(pair)) {
        rows.push([FALSE_MERGE, ...pair.split("\u0000")]);
      }
    }
    for (const pair of truth) {
      if (!found.has(pair)) {
        rows.push([MISSED, ...pair.split("\u0000")]);
      }
    }
    return rows.sort(compareRows);
  }

  // Helpers
  private static score(first: StoredRecord, second: StoredRecord): number {
    if (first.email !== "" && first.email === second.email) {
      return 1;
    }
    if (first.name === "" || second.name === "") {
      return 0;
    }
    return JARO_WEIGHT * jaroWinkler(first.name, second.name) + JACCARD_WEIGHT * tokenJaccard(first.name, second.name);
  }

  private mayMerge(left: string[], right: string[]): boolean {
    return left.every((a) => right.every((b) => this.similarity(a, b) >= MERGE_FLOOR));
  }

  private entityOf(recordId: string): string[] {
    if (!this.records.has(recordId)) {
      return [];
    }
    return this.clusters().find((group) => group.includes(recordId)) as string[];
  }

  // Most filled fields first, then the longer normalized name, then the smaller id.
  private canonicalBefore(candidate: string, best: string): boolean {
    const a = this.records.get(candidate) as StoredRecord;
    const b = this.records.get(best) as StoredRecord;
    const filledA = Number(a.name !== "") + Number(a.email !== "");
    const filledB = Number(b.name !== "") + Number(b.email !== "");
    if (filledA !== filledB) {
      return filledA > filledB;
    }
    if (a.name.length !== b.name.length) {
      return a.name.length > b.name.length;
    }
    return compareText(candidate, best) < 0;
  }
}
