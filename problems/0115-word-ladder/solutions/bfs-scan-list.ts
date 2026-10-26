function oneApart(first: string, second: string): boolean {
  let differences = 0;
  for (let i = 0; i < first.length; i++) {
    if (first[i] !== second[i] && ++differences > 1) return false;
  }
  return differences === 1;
}

export function ladderLength(beginWord: string, endWord: string, wordList: string[]): number {
  if (!wordList.includes(endWord)) return 0;
  let unvisited = wordList.filter((word) => word !== beginWord);
  let level = [beginWord];
  for (let words = 1; level.length > 0; words++) {
    if (level.includes(endWord)) return words;
    // Compare against every word not reached yet; the neighbors leave the list.
    const next: string[] = [];
    for (const word of level) {
      const remaining: string[] = [];
      for (const candidate of unvisited) {
        if (oneApart(word, candidate)) next.push(candidate);
        else remaining.push(candidate);
      }
      unvisited = remaining;
    }
    level = next;
  }
  return 0;
}
