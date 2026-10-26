const OPENER_OF = new Map([
  [")", "("],
  ["]", "["],
  ["}", "{"],
]);

export function isValid(s: string): boolean {
  const openBrackets: string[] = [];
  for (const character of s) {
    const opener = OPENER_OF.get(character);
    if (opener === undefined) {
      openBrackets.push(character);
    } else if (openBrackets.pop() !== opener) {
      // pop() on an empty array returns undefined, which never equals an opener.
      return false;
    }
  }
  return openBrackets.length === 0;
}
