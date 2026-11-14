export function checkValidString(s: string): boolean {
  // possible[k] is true when some choice of wildcards gives the prefix an open count of k.
  let possible = new Array<boolean>(s.length + 2).fill(false);
  possible[0] = true;
  for (const char of s) {
    const following = new Array<boolean>(s.length + 2).fill(false);
    let any = false;
    for (let open = 0; open <= s.length; open++) {
      if (!possible[open]) {
        continue;
      }
      if (char !== ")") {
        following[open + 1] = true; // "(" or a wildcard as "("
      }
      if (char !== "(" && open > 0) {
        following[open - 1] = true; // ")" or a wildcard as ")"
      }
      if (char === "*") {
        following[open] = true; // a wildcard as nothing
      }
      any = true;
    }
    if (!any) {
      return false;
    }
    possible = following;
  }
  return possible[0];
}
