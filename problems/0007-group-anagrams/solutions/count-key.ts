const ALPHABET_SIZE = 26;
const BASE = "a".charCodeAt(0);

export function groupAnagrams(strs: string[]): string[][] {
  const groups = new Map<string, string[]>();
  for (const word of strs) {
    const counts = new Array<number>(ALPHABET_SIZE).fill(0);
    for (let i = 0; i < word.length; i++) {
      counts[word.charCodeAt(i) - BASE]++;
    }
    // Map keys compare arrays by reference, so the counts become a string key.
    const key = counts.join(",");
    const group = groups.get(key);
    if (group === undefined) {
      groups.set(key, [word]);
    } else {
      group.push(word);
    }
  }
  return [...groups.values()];
}
