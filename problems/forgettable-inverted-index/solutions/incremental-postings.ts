function countTerms(tokens: string[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const token of tokens) {
    counts.set(token, (counts.get(token) ?? 0) + 1);
  }
  return counts;
}

function compareText(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export class ForgettableIndex {
  private readonly k1: number;
  private readonly b: number;
  // Each document's distinct terms: what forgetting it must take out of the postings.
  private readonly terms = new Map<string, string[]>();
  private readonly lengths = new Map<string, number>();
  // Term to the documents that hold it, with how many times each holds it.
  private readonly postings = new Map<string, Map<string, number>>();
  private totalLength = 0;

  constructor(k1: number, b: number) {
    this.k1 = k1;
    this.b = b;
  }

  add(docId: string, tokens: string[]): boolean {
    if (this.lengths.has(docId)) {
      return false;
    }
    this.index(docId, tokens);
    return true;
  }

  update(docId: string, tokens: string[]): boolean {
    if (!this.lengths.has(docId)) {
      return false;
    }
    this.unindex(docId);
    this.index(docId, tokens);
    return true;
  }

  forget(docId: string): boolean {
    if (!this.lengths.has(docId)) {
      return false;
    }
    this.unindex(docId);
    return true;
  }

  search(query: string[], topN: number): string[] {
    const scores = this.scores(query);
    return [...scores.keys()]
      .sort((a, b) => scores.get(b)! - scores.get(a)! || compareText(a, b))
      .slice(0, topN);
  }

  score(query: string[], docId: string): number {
    return this.scores(query).get(docId) ?? 0;
  }

  private index(docId: string, tokens: string[]): void {
    const counts = countTerms(tokens);
    for (const [term, count] of counts) {
      let holders = this.postings.get(term);
      if (holders === undefined) {
        holders = new Map();
        this.postings.set(term, holders);
      }
      holders.set(docId, count);
    }
    this.terms.set(docId, [...counts.keys()]);
    this.lengths.set(docId, tokens.length);
    this.totalLength += tokens.length;
  }

  private unindex(docId: string): void {
    for (const term of this.terms.get(docId)!) {
      const holders = this.postings.get(term)!;
      holders.delete(docId);
      if (holders.size === 0) {
        this.postings.delete(term);
      }
    }
    this.terms.delete(docId);
    this.totalLength -= this.lengths.get(docId)!;
    this.lengths.delete(docId);
  }

  // BM25 scores of the documents that hold a query term; the others get no entry.
  private scores(query: string[]): Map<string, number> {
    const scores = new Map<string, number>();
    if (this.totalLength === 0) {
      return scores; // no document holds a single token, so none holds a query term
    }
    const documentCount = this.lengths.size;
    const averageLength = this.totalLength / documentCount;
    for (const term of new Set(query)) {
      const holders = this.postings.get(term) ?? new Map<string, number>();
      const idf = Math.log(1 + (documentCount - holders.size + 0.5) / (holders.size + 0.5));
      for (const [docId, count] of holders) {
        const lengthRatio = this.lengths.get(docId)! / averageLength;
        const saturation = count + this.k1 * (1 - this.b + this.b * lengthRatio);
        scores.set(docId, (scores.get(docId) ?? 0) + (idf * count * (this.k1 + 1)) / saturation);
      }
    }
    return scores;
  }
}
