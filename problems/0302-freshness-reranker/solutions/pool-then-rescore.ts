const HALF = 0.5;
const NO_BOOST = 1;

interface Scored {
  score: number;
  index: number;
}

// Higher score first, then the lower index.
function byRank(a: Scored, b: Scored): number {
  return b.score - a.score || a.index - b.index;
}

export function rerankByFreshness(
  candidates: string[][],
  relevance: number[],
  ageHours: number[],
  halfLifeHours: number,
  boostSources: string[],
  boostFactors: number[],
  poolSize: number,
): string[] {
  const boostOf = new Map(boostSources.map((source, index) => [source, boostFactors[index]]));
  const pool = candidates
    .map((_, index) => index)
    .sort((a, b) => relevance[b] - relevance[a] || a - b)
    .slice(0, poolSize);
  const bestCopy = new Map<string, Scored>();
  for (const index of pool) {
    const [, canonicalId, source] = candidates[index];
    const decay = HALF ** (ageHours[index] / halfLifeHours);
    const entry = { score: relevance[index] * decay * (boostOf.get(source) ?? NO_BOOST), index };
    const kept = bestCopy.get(canonicalId);
    if (kept === undefined || byRank(entry, kept) < 0) {
      bestCopy.set(canonicalId, entry);
    }
  }
  return [...bestCopy.values()].sort(byRank).map((entry) => candidates[entry.index][0]);
}
