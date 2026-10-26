export function minDistance(word1: string, word2: string): number {
  // The distance is symmetric (insertions and deletions swap roles), so let the rows run
  // along the shorter word.
  const [longer, shorter] = word1.length >= word2.length ? [word1, word2] : [word2, word1];
  // previous[j] is the distance between longer[:i - 1] and shorter[:j].
  let previous = Int32Array.from({ length: shorter.length + 1 }, (_, j) => j);
  let current = new Int32Array(shorter.length + 1);
  for (let i = 1; i <= longer.length; i++) {
    current[0] = i;
    for (let j = 1; j <= shorter.length; j++) {
      current[j] =
        longer[i - 1] === shorter[j - 1]
          ? previous[j - 1]
          : 1 + Math.min(previous[j], current[j - 1], previous[j - 1]);
    }
    [previous, current] = [current, previous];
  }
  return previous[shorter.length];
}
