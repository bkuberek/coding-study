export function minRemoveToMakeValid(s: string): string {
  const deleted = new Array<boolean>(s.length).fill(false);
  const openPositions: number[] = [];
  for (let position = 0; position < s.length; position++) {
    if (s[position] === "(") {
      openPositions.push(position);
    } else if (s[position] === ")") {
      if (openPositions.length > 0) {
        openPositions.pop(); // matches the most recent unmatched opener
      } else {
        deleted[position] = true; // nothing open: this closer can never match
      }
    }
  }
  for (const position of openPositions) {
    deleted[position] = true; // openers that were never closed
  }
  let result = "";
  for (let position = 0; position < s.length; position++) {
    if (!deleted[position]) {
      result += s[position];
    }
  }
  return result;
}
