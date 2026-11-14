export function longestPalindrome(s: string): string {
  // Interleave a separator so every palindrome has odd length: "ab" becomes "|a|b|".
  const t = "|" + s.split("").join("|") + "|";
  // radius[i] is how far the palindrome centered at t[i] extends to each side.
  const radius = new Array<number>(t.length).fill(0);
  let center = 0;
  let right = 0; // the palindrome reaching furthest right is t[2 * center - right .. right]
  let best = 0;
  for (let i = 0; i < t.length; i++) {
    if (i < right) {
      // Mirror of i around center; its radius is valid up to the right boundary.
      radius[i] = Math.min(right - i, radius[2 * center - i]);
    }
    while (
      i - radius[i] - 1 >= 0 &&
      i + radius[i] + 1 < t.length &&
      t[i - radius[i] - 1] === t[i + radius[i] + 1]
    ) {
      radius[i]++;
    }
    if (i + radius[i] > right) {
      center = i;
      right = i + radius[i];
    }
    if (radius[i] > radius[best]) {
      best = i;
    }
  }
  // A radius r around position i of t covers r characters of s starting at (i - r) / 2.
  const start = (best - radius[best]) >> 1;
  return s.slice(start, start + radius[best]);
}
