const CHARACTERS_PER_TOKEN = 4;
const PERMILLE = 1000;
const PERMILLE_SQUARED = PERMILLE * PERMILLE;
const NO_SOURCE_VERSION = 0;

interface Entry {
  key: string;
  response: string;
  embedding: number[] | null;
  source: string;
  version: number;
  sequence: number;
}

interface Tier {
  calls: number;
  fullTokens: number;
  cachedTokens: number;
  outputTokens: number;
  cost: number;
}

interface Attempt {
  status: string;
  called: number[];
  text: string;
}

/** Trim, collapse each run of spaces, tabs and newlines to one space, lowercase ASCII. */
function normalize(prompt: string): string {
  return prompt
    .replace(/^[ \t\n]+|[ \t\n]+$/g, "")
    .replace(/[ \t\n]+/g, " ")
    .toLowerCase();
}

function tokenCount(text: string): number {
  return Math.ceil(text.length / CHARACTERS_PER_TOKEN);
}

/** Integer division rounded toward negative infinity, exact for the sizes of this problem. */
function floorDiv(numerator: number, denominator: number): number {
  return (numerator - mod(numerator, denominator)) / denominator;
}

function mod(numerator: number, denominator: number): number {
  return ((numerator % denominator) + denominator) % denominator;
}

function floorPercent(part: number, whole: number): number {
  return whole > 0 ? floorDiv(100 * part, whole) : 0;
}

function integerSquareRoot(value: number): number {
  let root = Math.floor(Math.sqrt(value));
  while (root * root > value) {
    root -= 1;
  }
  while ((root + 1) * (root + 1) <= value) {
    root += 1;
  }
  return root;
}

function dot(a: number[], b: number[]): number {
  return a.reduce((total, x, index) => total + x * b[index], 0);
}

export class CacheRouter {
  private readonly entries = new Map<string, Entry>();
  private nextSequence = 0;
  private readonly sourceVersions = new Map<string, number>();
  private exactHits = 0;
  private semanticHits = 0;
  private misses = 0;
  private limits: number[] = [];
  private labelTiers = new Map<string, number>();
  private markers: string[] = [];
  private prices: number[][] = [[], [], []];
  private readonly prefixTokens = new Map<string, number>();
  private threshold = PERMILLE;
  private warm: Set<string>[] = [];
  private tiers: Tier[] = [];
  private requests = 0;
  private totalCost = 0;
  private totalBaseline = 0;

  // Level 1
  key(prompt: string): string {
    return normalize(prompt);
  }

  put(prompt: string, response: string): boolean {
    return this.insert(normalize(prompt), response, null, "");
  }

  lookup(prompt: string): string[] {
    const entry = this.entries.get(normalize(prompt));
    if (entry === undefined) {
      this.misses += 1;
      return ["miss"];
    }
    this.exactHits += 1;
    return ["hit", entry.response];
  }

  stats(): number[] {
    const hits = this.exactHits + this.semanticHits;
    return [hits, this.misses, this.entries.size, floorPercent(hits, hits + this.misses)];
  }

  // Level 2
  putSemantic(prompt: string, embedding: number[], response: string, source: string): boolean {
    return this.insert(normalize(prompt), response, [...embedding], source);
  }

  lookupSemantic(prompt: string, embedding: number[], threshold: number): string[] {
    const exact = this.entries.get(normalize(prompt));
    if (exact !== undefined) {
      this.exactHits += 1;
      return ["hit", "exact", exact.response];
    }
    const best = this.nearest(embedding, threshold);
    if (best === null) {
      this.misses += 1;
      return ["miss"];
    }
    this.semanticHits += 1;
    return ["hit", "semantic", best.entry.response, best.entry.key, String(best.permille)];
  }

  setSourceVersion(source: string, version: number): number {
    this.sourceVersions.set(source, version);
    const stale = [...this.entries.values()].filter(
      (entry) => entry.source === source && entry.version !== version,
    );
    for (const entry of stale) {
      this.entries.delete(entry.key);
    }
    return stale.length;
  }

  // Level 3
  configureRouting(tierLimits: number[], labels: string[], labelTiers: number[], invalidMarkers: string[]): void {
    this.limits = [...tierLimits];
    this.labelTiers = new Map(labels.map((label, index) => [label, labelTiers[index]]));
    this.markers = [...invalidMarkers];
    this.warm = this.limits.map(() => new Set<string>());
    this.tiers = this.limits.map(() => ({ calls: 0, fullTokens: 0, cachedTokens: 0, outputTokens: 0, cost: 0 }));
  }

  route(label: string, promptTokens: number): number {
    const start = this.labelTiers.get(label) ?? this.limits.length - 1;
    for (let tier = start; tier < this.limits.length; tier++) {
      if (promptTokens <= this.limits[tier]) {
        return tier;
      }
    }
    return -1;
  }

  answer(label: string, promptTokens: number, answers: string[]): string[] {
    const { status, called, text } = this.attempt(label, promptTokens, answers);
    return [status, called.join(">"), text];
  }

  // Level 4
  setPrices(inputPrices: number[], outputPrices: number[], cachedPrices: number[]): void {
    this.prices = [[...inputPrices], [...outputPrices], [...cachedPrices]];
  }

  definePrefix(prefixId: string, tokens: number): void {
    this.prefixTokens.set(prefixId, tokens);
  }

  setThreshold(threshold: number): void {
    this.threshold = threshold;
  }

  handle(
    prompt: string,
    embedding: number[],
    label: string,
    source: string,
    answers: string[],
    prefixId: string,
  ): string[] {
    const tokens = tokenCount(prompt);
    const hit = this.lookupSemantic(prompt, embedding, this.threshold);
    let status: string;
    let called: number[] = [];
    let text: string;
    let cost = 0;
    if (hit[0] === "hit") {
      status = hit[1];
      text = hit[2];
    } else {
      ({ status, called, text } = this.attempt(label, tokens, answers));
      cost = called.reduce((total, tier) => total + this.bill(tier, tokens, answers[tier], prefixId), 0);
      if (status === "ok" || status === "escalated") {
        this.putSemantic(prompt, embedding, text, source);
      }
    }
    const baseline = this.baseline(tokens, answers);
    this.requests += 1;
    this.totalCost += cost;
    this.totalBaseline += baseline;
    return [status, called.join(">"), text, String(cost), String(baseline)];
  }

  report(): string[][] {
    const savings = this.totalBaseline - this.totalCost;
    const rows = [
      [
        "total",
        String(this.requests),
        String(this.totalCost),
        String(this.totalBaseline),
        String(savings),
        String(floorPercent(savings, this.totalBaseline)),
      ],
      ["cache", String(this.exactHits), String(this.semanticHits), String(this.misses)],
    ];
    this.tiers.forEach((tier, index) => {
      rows.push([
        "tier",
        String(index),
        String(tier.calls),
        String(tier.fullTokens),
        String(tier.cachedTokens),
        String(tier.outputTokens),
        String(tier.cost),
      ]);
    });
    return rows;
  }

  // Helpers
  private insert(key: string, response: string, embedding: number[] | null, source: string): boolean {
    if (this.entries.has(key)) {
      return false;
    }
    const version = source === "" ? 0 : (this.sourceVersions.get(source) ?? NO_SOURCE_VERSION);
    this.entries.set(key, { key, response, embedding, source, version, sequence: this.nextSequence });
    this.nextSequence += 1;
    return true;
  }

  private nearest(query: number[], threshold: number): { entry: Entry; permille: number } | null {
    const queryNorm = dot(query, query);
    let best: { entry: Entry; permille: number; dot: number; norm: number } | null = null;
    for (const entry of this.entries.values()) {
      if (entry.embedding === null || queryNorm === 0) {
        continue;
      }
      const product = dot(query, entry.embedding);
      const norm = dot(entry.embedding, entry.embedding);
      if (product <= 0 || norm === 0) {
        continue;
      }
      const permille = integerSquareRoot(floorDiv(PERMILLE_SQUARED * product * product, queryNorm * norm));
      if (permille < threshold) {
        continue;
      }
      // product^2 / norm is the squared cosine times the query's norm: a larger value is closer.
      const closer = best === null || product * product * best.norm > best.dot * best.dot * norm;
      if (closer) {
        best = { entry, permille, dot: product, norm };
      }
    }
    return best === null ? null : { entry: best.entry, permille: best.permille };
  }

  private isValid(text: string): boolean {
    return text.replace(/^[ \t\n]+|[ \t\n]+$/g, "") !== "" && !this.markers.some((marker) => text.includes(marker));
  }

  private attempt(label: string, promptTokens: number, answers: string[]): Attempt {
    const tier = this.route(label, promptTokens);
    if (tier < 0) {
      return { status: "too_long", called: [], text: "" };
    }
    if (this.isValid(answers[tier])) {
      return { status: "ok", called: [tier], text: answers[tier] };
    }
    if (tier === this.limits.length - 1) {
      return { status: "invalid", called: [tier], text: answers[tier] };
    }
    const higher = answers[tier + 1];
    return { status: this.isValid(higher) ? "escalated" : "invalid", called: [tier, tier + 1], text: higher };
  }

  private bill(tier: number, tokens: number, answer: string, prefixId: string): number {
    const [inputPrice, outputPrice, cachedPrice] = this.prices.map((prices) => prices[tier]);
    const reused = prefixId !== "" && this.warm[tier].has(prefixId);
    const cached = reused ? Math.min(this.prefixTokens.get(prefixId) ?? 0, tokens) : 0;
    const output = tokenCount(answer);
    const cost = (tokens - cached) * inputPrice + cached * cachedPrice + output * outputPrice;
    if (prefixId !== "") {
      this.warm[tier].add(prefixId);
    }
    const ledger = this.tiers[tier];
    ledger.calls += 1;
    ledger.fullTokens += tokens - cached;
    ledger.cachedTokens += cached;
    ledger.outputTokens += output;
    ledger.cost += cost;
    return cost;
  }

  private baseline(tokens: number, answers: string[]): number {
    if (tokens > this.limits[this.limits.length - 1]) {
      return 0;
    }
    return tokens * this.prices[0][this.limits.length - 1] + tokenCount(answers[answers.length - 1]) * this.prices[1][this.limits.length - 1];
  }
}
