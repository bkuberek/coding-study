export function numDecodings(s: string): number {
  // Before digit i: oneBack counts readings of s[0..i) and twoBack those of s[0..i - 1).
  let twoBack = 0;
  let oneBack = 1;
  for (let i = 0; i < s.length; i++) {
    let current = s[i] !== "0" ? oneBack : 0;
    if (i > 0) {
      const pair = (s.charCodeAt(i - 1) - 48) * 10 + (s.charCodeAt(i) - 48);
      if (pair >= 10 && pair <= 26) {
        current += twoBack;
      }
    }
    twoBack = oneBack;
    oneBack = current;
  }
  return oneBack;
}
