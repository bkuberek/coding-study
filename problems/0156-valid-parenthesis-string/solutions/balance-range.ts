export function checkValidString(s: string): boolean {
  // The possible open counts of the prefix are exactly the integers in [lowest, highest].
  let lowest = 0;
  let highest = 0;
  for (const char of s) {
    if (char === "(") {
      lowest++;
      highest++;
    } else if (char === ")") {
      lowest--;
      highest--;
    } else {
      lowest--; // the wildcard as ")"
      highest++; // the wildcard as "("
    }
    if (highest < 0) {
      return false; // even with every wildcard as "(", too many ")"
    }
    lowest = Math.max(lowest, 0); // a negative count is not a real choice
  }
  return lowest === 0;
}
