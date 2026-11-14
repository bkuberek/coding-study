export function isInterleave(s1: string, s2: string, s3: string): boolean {
  if (s1.length + s2.length !== s3.length) {
    return false;
  }
  // known[i][j] caches whether s1[i:] and s2[j:] interleave to s3[i + j:]:
  // -1 unknown, 0 no, 1 yes.
  const known = Array.from({ length: s1.length + 1 }, () => new Int8Array(s2.length + 1).fill(-1));
  const solve = (i: number, j: number): boolean => {
    if (i === s1.length && j === s2.length) {
      return true;
    }
    if (known[i][j] < 0) {
      // The next character of s3 comes from s1 or from s2.
      const fits =
        (i < s1.length && s1[i] === s3[i + j] && solve(i + 1, j)) ||
        (j < s2.length && s2[j] === s3[i + j] && solve(i, j + 1));
      known[i][j] = fits ? 1 : 0;
    }
    return known[i][j] === 1;
  };
  return solve(0, 0);
}
