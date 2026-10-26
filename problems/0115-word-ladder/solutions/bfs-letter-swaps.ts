const LETTERS = "abcdefghijklmnopqrstuvwxyz";

export function ladderLength(beginWord: string, endWord: string, wordList: string[]): number {
  // Words still available; a word leaves the set the moment it is reached.
  const available = new Set(wordList);
  if (!available.has(endWord)) return 0;
  available.delete(beginWord);
  let level = [beginWord];
  for (let words = 1; level.length > 0; words++) {
    const next: string[] = [];
    for (const word of level) {
      if (word === endWord) return words;
      for (let position = 0; position < word.length; position++) {
        const prefix = word.slice(0, position);
        const suffix = word.slice(position + 1);
        for (const letter of LETTERS) {
          const candidate = prefix + letter + suffix;
          if (available.delete(candidate)) next.push(candidate);
        }
      }
    }
    level = next;
  }
  return 0;
}
