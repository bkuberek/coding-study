export function isMatch(s: string, p: string): boolean {
  const rows = s.length;
  const columns = p.length;
  // matches[i][j]: s[:i] matches p[:j].
  const matches = Array.from({ length: rows + 1 }, () => new Array<boolean>(columns + 1).fill(false));
  matches[0][0] = true;
  for (let i = 0; i <= rows; i++) {
    for (let j = 1; j <= columns; j++) {
      if (p[j - 1] === "*") {
        // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
        const repeated = i > 0 && (p[j - 2] === s[i - 1] || p[j - 2] === ".") && matches[i - 1][j];
        matches[i][j] = matches[i][j - 2] || repeated;
      } else {
        matches[i][j] = i > 0 && (p[j - 1] === s[i - 1] || p[j - 1] === ".") && matches[i - 1][j - 1];
      }
    }
  }
  return matches[rows][columns];
}
