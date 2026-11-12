export function countByPrefix(words: string[], prefixes: string[]): number[] {
  return prefixes.map((prefix) => {
    let count = 0;
    for (const word of words) {
      if (word.startsWith(prefix)) {
        count++;
      }
    }
    return count;
  });
}
