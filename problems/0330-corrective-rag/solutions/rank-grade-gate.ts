type Verdict = "relevant" | "ambiguous" | "irrelevant";

interface Passage {
  readonly id: string;
  readonly embedding: number[];
  readonly length: number;
  readonly text: string;
}

interface Piece {
  readonly itemId: string;
  readonly cite: string;
  readonly text: string;
}

interface Attempt {
  readonly query: string;
  readonly count: number;
}

function dot(a: number[], b: number[]): number {
  let total = 0;
  for (let i = 0; i < a.length; i++) {
    total += a[i] * b[i];
  }
  return total;
}

/** The sentences of a text, each with its period: the text is split after every period. */
function sentences(text: string): string[] {
  return text
    .split(".")
    .slice(0, -1)
    .map((piece) => piece.trim() + ".");
}

/** One token per word and one per period. */
function tokens(text: string): number {
  let periods = 0;
  for (const char of text) {
    if (char === ".") {
      periods++;
    }
  }
  return text.split(" ").length + periods;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export class CorrectiveRag {
  private readonly passages = new Map<string, Passage>();
  private readonly queries = new Map<string, number[]>();
  private readonly verdicts = new Map<string, Verdict>();
  private readonly fallbacks = new Map<string, Map<string, string>>();
  private readonly rewrites = new Map<string, string[]>();

  // Level 1
  addPassage(passageId: string, embedding: number[], text: string): boolean {
    if (this.passages.has(passageId)) {
      return false;
    }
    this.passages.set(passageId, { id: passageId, embedding, length: dot(embedding, embedding), text });
    return true;
  }

  addQuery(query: string, embedding: number[]): boolean {
    if (this.queries.has(query)) {
      return false;
    }
    this.queries.set(query, embedding);
    return true;
  }

  addVerdict(query: string, itemId: string, verdict: string): boolean {
    const key = verdictKey(query, itemId);
    if (this.verdicts.has(key)) {
      return false;
    }
    this.verdicts.set(key, verdict as Verdict);
    return true;
  }

  retrieve(query: string, k: number): string[][] {
    return this.top(query, k).map((passage) => [passage.id, this.verdict(query, passage.id)]);
  }

  keepRelevant(query: string, k: number): string[] {
    return this.top(query, k)
      .filter((passage) => this.verdict(query, passage.id) === "relevant")
      .map((passage) => passage.id);
  }

  verdictCounts(query: string, k: number): number[] {
    const counts = [0, 0, 0];
    for (const passage of this.top(query, k)) {
      counts[["relevant", "ambiguous", "irrelevant"].indexOf(this.verdict(query, passage.id))]++;
    }
    return counts;
  }

  // Level 2
  addFallback(query: string, fallbackId: string, text: string): boolean {
    let items = this.fallbacks.get(query);
    if (items === undefined) {
      items = new Map();
      this.fallbacks.set(query, items);
    }
    if (items.has(fallbackId)) {
      return false;
    }
    items.set(fallbackId, text);
    return true;
  }

  decide(query: string, k: number): string {
    return this.decision(query, this.top(query, k));
  }

  evidence(query: string, k: number): string[][] {
    return this.pieces(query, k).map((piece) => [piece.itemId, piece.text]);
  }

  // Level 3
  addRewrite(query: string, rewrite: string): boolean {
    let listed = this.rewrites.get(query);
    if (listed === undefined) {
      listed = [];
      this.rewrites.set(query, listed);
    }
    if (rewrite === query || listed.includes(rewrite)) {
      return false;
    }
    listed.push(rewrite);
    return true;
  }

  attempts(query: string, k: number, need: number, maxRetries: number): string[][] {
    const { tried, chosen } = this.search(query, k, need, maxRetries);
    return tried.map((attempt, index) => [
      attempt.query,
      this.decide(attempt.query, k),
      String(attempt.count),
      index === chosen ? "chosen" : "tried",
    ]);
  }

  // Level 4
  groundedContext(query: string, k: number, need: number, maxRetries: number, budget: number): string[][] {
    return this.grounded(query, k, need, maxRetries, budget).rows;
  }

  answer(query: string, k: number, need: number, maxRetries: number, budget: number, minSupport: number): string {
    const { searched, rows } = this.grounded(query, k, need, maxRetries, budget);
    const sources = new Map<string, string>();
    for (const [number, cite] of rows) {
      if (!sources.has(number)) {
        sources.set(number, cite);
      }
    }
    if (sources.size < minSupport) {
      return `not enough evidence: ${sources.size} of ${minSupport} sources`;
    }
    const lines = [`question: ${query}`, `searched: ${searched}`];
    for (const [number, , , text] of rows) {
      lines.push(`[${number}] ${text}`);
    }
    const listed = [...sources].map(([number, cite]) => `[${number}] ${cite}`);
    lines.push(`sources: ${listed.join(", ")}`);
    return lines.join("\n");
  }

  // Helpers
  private verdict(query: string, itemId: string): Verdict {
    return this.verdicts.get(verdictKey(query, itemId)) ?? "irrelevant";
  }

  /**
   * The k best passages by cosine, compared exactly. With the query's length common to all,
   * cos(a) > cos(b) exactly when dot_a * |dot_a| * |b|^2 > dot_b * |dot_b| * |a|^2. Every product
   * stays below 2^53 for the vectors of the constraints, so plain numbers are exact.
   */
  private top(query: string, k: number): Passage[] {
    const embedding = this.queries.get(query);
    if (embedding === undefined || embedding.every((value) => value === 0)) {
      return [];
    }
    const scored: { passage: Passage; signed: number }[] = [];
    for (const passage of this.passages.values()) {
      if (passage.length > 0) {
        const d = dot(embedding, passage.embedding);
        scored.push({ passage, signed: d * Math.abs(d) });
      }
    }
    scored.sort(
      (a, b) =>
        b.signed * a.passage.length - a.signed * b.passage.length || compareText(a.passage.id, b.passage.id),
    );
    return scored.slice(0, k).map((entry) => entry.passage);
  }

  private decision(query: string, top: Passage[]): string {
    const verdicts = top.map((passage) => this.verdict(query, passage.id));
    const relevant = verdicts.includes("relevant");
    const ambiguous = verdicts.includes("ambiguous");
    if (relevant) {
      return ambiguous ? "refine" : "keep";
    }
    return ambiguous ? "blend" : "fallback";
  }

  private pieces(query: string, k: number): Piece[] {
    const top = this.top(query, k);
    const found: Piece[] = [];
    for (const passage of top) {
      const verdict = this.verdict(query, passage.id);
      if (verdict === "relevant") {
        found.push({ itemId: passage.id, cite: passage.id, text: passage.text });
      } else if (verdict === "ambiguous") {
        sentences(passage.text).forEach((sentence, index) => {
          const sentenceId = `${passage.id}#${index + 1}`;
          if (this.verdict(query, sentenceId) === "relevant") {
            found.push({ itemId: sentenceId, cite: passage.id, text: sentence });
          }
        });
      }
    }
    const action = this.decision(query, top);
    if (action === "blend" || action === "fallback") {
      for (const [fallbackId, text] of this.fallbacks.get(query) ?? []) {
        if (this.verdict(query, fallbackId) === "relevant") {
          found.push({ itemId: fallbackId, cite: fallbackId, text });
        }
      }
    }
    return found;
  }

  /** The attempts made, with their evidence counts, and the index of the chosen one. */
  private search(query: string, k: number, need: number, maxRetries: number): { tried: Attempt[]; chosen: number } {
    const candidates = [query, ...(this.rewrites.get(query) ?? []).slice(0, maxRetries)];
    const tried: Attempt[] = [];
    let best = 0;
    for (const asked of candidates) {
      const count = this.pieces(asked, k).length;
      tried.push({ query: asked, count });
      if (count >= need) {
        return { tried, chosen: tried.length - 1 };
      }
      if (count > tried[best].count) {
        best = tried.length - 1;
      }
    }
    return { tried, chosen: best };
  }

  private grounded(
    query: string,
    k: number,
    need: number,
    maxRetries: number,
    budget: number,
  ): { searched: string; rows: string[][] } {
    const { tried, chosen } = this.search(query, k, need, maxRetries);
    const searched = tried[chosen].query;
    const numbers = new Map<string, number>();
    const rows: string[][] = [];
    let remaining = budget;
    for (const piece of this.pieces(searched, k)) {
      const size = tokens(piece.text);
      if (size > remaining) {
        break;
      }
      remaining -= size;
      if (!numbers.has(piece.cite)) {
        numbers.set(piece.cite, numbers.size + 1);
      }
      rows.push([String(numbers.get(piece.cite)), piece.cite, String(size), piece.text]);
    }
    return { searched, rows };
  }
}

/** Queries and item ids never hold a "|", so the joined key is unambiguous. */
function verdictKey(query: string, itemId: string): string {
  return `${query}|${itemId}`;
}
