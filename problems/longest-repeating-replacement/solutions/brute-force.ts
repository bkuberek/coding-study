export function characterReplacement(s: string, k: number): number {
  let best = 0;
  for (let start = 0; start < s.length; start++) {
    const counts = new Int32Array(26);
    let most = 0;
    for (let end = start; end < s.length; end++) {
      const letter = s.charCodeAt(end) - 65;
      most = Math.max(most, ++counts[letter]);
      if (end - start + 1 - most > k) {
        break;
      }
      best = Math.max(best, end - start + 1);
    }
  }
  return best;
}
