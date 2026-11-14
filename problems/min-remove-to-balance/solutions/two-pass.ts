export function minRemoveToMakeValid(s: string): string {
  // Pass 1, left to right: drop every closer that finds nothing open.
  const kept: string[] = [];
  let openCount = 0;
  for (const character of s) {
    if (character === ")") {
      if (openCount === 0) {
        continue;
      }
      openCount--;
    } else if (character === "(") {
      openCount++;
    }
    kept.push(character);
  }
  // Pass 2, right to left: drop the last `openCount` openers, which are never closed.
  const result: string[] = [];
  for (let i = kept.length - 1; i >= 0; i--) {
    if (kept[i] === "(" && openCount > 0) {
      openCount--;
      continue;
    }
    result.push(kept[i]);
  }
  return result.reverse().join("");
}
