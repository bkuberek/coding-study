export function characterReplacement(s: string, k: number): number {
  let best = 0;
  for (const target of new Set(s)) {
    let left = 0;
    let others = 0;
    for (let right = 0; right < s.length; right++) {
      if (s[right] !== target) {
        others++;
      }
      while (others > k) {
        if (s[left] !== target) {
          others--;
        }
        left++;
      }
      best = Math.max(best, right - left + 1);
    }
  }
  return best;
}
