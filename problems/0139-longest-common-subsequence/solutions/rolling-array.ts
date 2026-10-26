export function longestCommonSubsequence(text1: string, text2: string): number {
  // The answer is symmetric, so let the rows run along the shorter string.
  const [longer, shorter] = text1.length >= text2.length ? [text1, text2] : [text2, text1];
  // previous[j] is the answer for the prefixes longer[:i - 1] and shorter[:j].
  let previous = new Int32Array(shorter.length + 1);
  let current = new Int32Array(shorter.length + 1);
  for (let i = 1; i <= longer.length; i++) {
    for (let j = 1; j <= shorter.length; j++) {
      current[j] =
        longer[i - 1] === shorter[j - 1]
          ? previous[j - 1] + 1
          : Math.max(previous[j], current[j - 1]);
    }
    [previous, current] = [current, previous];
  }
  return previous[shorter.length];
}
