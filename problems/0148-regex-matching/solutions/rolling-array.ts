export function isMatch(s: string, p: string): boolean {
  const columns = p.length;
  // previous[j]: s[:i - 1] matches p[:j]; current[j]: s[:i] matches p[:j].
  let previous = new Array<boolean>(columns + 1).fill(false);
  let current = new Array<boolean>(columns + 1).fill(false);
  for (let i = 0; i <= s.length; i++) {
    current[0] = i === 0;
    for (let j = 1; j <= columns; j++) {
      if (p[j - 1] === "*") {
        // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
        const repeated = i > 0 && (p[j - 2] === s[i - 1] || p[j - 2] === ".") && previous[j];
        current[j] = current[j - 2] || repeated;
      } else {
        current[j] = i > 0 && (p[j - 1] === s[i - 1] || p[j - 1] === ".") && previous[j - 1];
      }
    }
    [previous, current] = [current, previous];
  }
  return previous[columns];
}
