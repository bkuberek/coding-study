function bestFirst(scores: Map<number, number>): number[] {
  return [...scores.keys()].sort((a, b) => scores.get(b)! - scores.get(a)! || a - b);
}

// Scores of the documents with a query term; the others get no entry, and so no rank.
function bm25Scores(documents: string[][], query: string[], k1: number, b: number): Map<number, number> {
  const postings = new Map<string, Map<number, number>>(query.map((term) => [term, new Map()]));
  documents.forEach((tokens, document) => {
    for (const token of tokens) {
      const counts = postings.get(token);
      if (counts !== undefined) {
        counts.set(document, (counts.get(document) ?? 0) + 1);
      }
    }
  });

  const documentCount = documents.length;
  const tokenCount = documents.reduce((total, tokens) => total + tokens.length, 0);
  const averageLength = tokenCount / documentCount;
  const scores = new Map<number, number>();
  for (const counts of postings.values()) {
    const holders = counts.size;
    const idf = Math.log(1 + (documentCount - holders + 0.5) / (holders + 0.5));
    for (const [document, count] of counts) {
      // A holder has at least one token, so the average length is above zero here.
      const lengthRatio = documents[document].length / averageLength;
      const saturation = count + k1 * (1 - b + b * lengthRatio);
      scores.set(document, (scores.get(document) ?? 0) + (idf * count * (k1 + 1)) / saturation);
    }
  }
  return scores;
}

export function hybridRank(
  documents: string[][],
  query: string[],
  vectorHits: number[],
  vectorScores: number[],
  k1: number,
  b: number,
  rrfK: number,
  topN: number,
): number[] {
  const keywordScores = bm25Scores(documents, query, k1, b);
  const similarity = new Map(vectorHits.map((document, i) => [document, vectorScores[i]]));
  const fused = new Map<number, number>();
  for (const scores of [keywordScores, similarity]) {
    bestFirst(scores).forEach((document, position) => {
      fused.set(document, (fused.get(document) ?? 0) + 1 / (rrfK + position + 1));
    });
  }
  return bestFirst(fused).slice(0, topN);
}
