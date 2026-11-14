export function groupAnagrams(strs: string[]): string[][] {
  const keys: string[] = [];
  const groups: string[][] = [];
  for (const word of strs) {
    const key = [...word].sort().join("");
    const index = keys.indexOf(key);
    if (index === -1) {
      keys.push(key);
      groups.push([word]);
    } else {
      groups[index].push(word);
    }
  }
  return groups;
}
