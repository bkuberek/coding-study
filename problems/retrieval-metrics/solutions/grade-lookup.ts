const RELEVANT_GRADE = 1;

function dcg(grades: number[]): number {
  let total = 0;
  grades.forEach((grade, index) => {
    const rank = index + 1;
    total += (2 ** grade - 1) / Math.log2(rank + 1);
  });
  return total;
}

// Recall, reciprocal rank and nDCG at k for one query, or null when nothing is relevant.
function queryMetrics(top: string[], gradeOf: Map<string, number>, k: number): number[] | null {
  const allGrades = [...gradeOf.values()];
  const relevant = allGrades.filter((grade) => grade >= RELEVANT_GRADE).length;
  if (relevant === 0) {
    return null;
  }
  const retrieved = top.map((doc) => gradeOf.get(doc) ?? 0);
  const found = retrieved.filter((grade) => grade >= RELEVANT_GRADE).length;
  const firstIndex = retrieved.findIndex((grade) => grade >= RELEVANT_GRADE);
  const reciprocalRank = firstIndex === -1 ? 0 : 1 / (firstIndex + 1);
  // The ideal ranking orders every judged document, retrieved or not, by grade.
  const ideal = allGrades.sort((a, b) => b - a).slice(0, k);
  return [found / relevant, reciprocalRank, dcg(retrieved) / dcg(ideal)];
}

export function retrievalMetrics(
  rankings: string[][],
  judgedDocs: string[][],
  grades: number[][],
  k: number,
): number[] {
  const scored: number[][] = [];
  rankings.forEach((ranking, query) => {
    const gradeOf = new Map(judgedDocs[query].map((doc, index) => [doc, grades[query][index]]));
    const metrics = queryMetrics(ranking.slice(0, k), gradeOf, k);
    if (metrics !== null) {
      scored.push(metrics);
    }
  });
  if (scored.length === 0) {
    return [0, 0, 0];
  }
  return [0, 1, 2].map(
    (metric) => scored.reduce((sum, row) => sum + row[metric], 0) / scored.length,
  );
}
