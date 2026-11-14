export function isMatch(s: string, p: string): boolean {
  // known[i][j] caches whether s[i:] matches p[j:]: -1 unknown, 0 no, 1 yes.
  const known = Array.from({ length: s.length + 1 }, () => new Int8Array(p.length + 1).fill(-1));
  const solve = (i: number, j: number): boolean => {
    if (j === p.length) {
      return i === s.length;
    }
    if (known[i][j] < 0) {
      const first = i < s.length && (p[j] === s[i] || p[j] === ".");
      let matched: boolean;
      if (j + 1 < p.length && p[j + 1] === "*") {
        // Skip "x*" entirely, or let it eat one more character and stay on it.
        matched = solve(i, j + 2) || (first && solve(i + 1, j));
      } else {
        matched = first && solve(i + 1, j + 1);
      }
      known[i][j] = matched ? 1 : 0;
    }
    return known[i][j] === 1;
  };
  return solve(0, 0);
}
