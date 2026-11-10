function dot(a: number[], b: number[]): number {
  let total = 0;
  for (let j = 0; j < a.length; j += 1) {
    total += a[j] * b[j];
  }
  return total;
}

export function topKCosine(query: number[], documents: number[][], k: number): number[] {
  const queryNorm = Math.sqrt(dot(query, query));
  if (queryNorm === 0) {
    return [];
  }
  const scored: { score: number; index: number }[] = [];
  documents.forEach((document, index) => {
    const documentNorm = Math.sqrt(dot(document, document));
    if (documentNorm !== 0) {
      scored.push({ score: dot(query, document) / (queryNorm * documentNorm), index });
    }
  });
  scored.sort((a, b) => b.score - a.score || a.index - b.index);
  return scored.slice(0, k).map((entry) => entry.index);
}
