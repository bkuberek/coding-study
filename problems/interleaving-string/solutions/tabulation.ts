export function isInterleave(s1: string, s2: string, s3: string): boolean {
  const rows = s1.length;
  const columns = s2.length;
  if (rows + columns !== s3.length) {
    return false;
  }
  // reach[i][j]: s1[:i] and s2[:j] interleave to s3[:i + j].
  const reach = Array.from({ length: rows + 1 }, () => new Array<boolean>(columns + 1).fill(false));
  reach[0][0] = true;
  for (let i = 0; i <= rows; i++) {
    for (let j = 0; j <= columns; j++) {
      // The last character of s3[:i + j] came from s1 or from s2.
      if (i > 0 && reach[i - 1][j] && s1[i - 1] === s3[i + j - 1]) {
        reach[i][j] = true;
      } else if (j > 0 && reach[i][j - 1] && s2[j - 1] === s3[i + j - 1]) {
        reach[i][j] = true;
      }
    }
  }
  return reach[rows][columns];
}
