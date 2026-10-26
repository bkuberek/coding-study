const LETTERS = "abcdefghijklmnopqrstuvwxyz";

export function ladderLength(beginWord: string, endWord: string, wordList: string[]): number {
  const available = new Set(wordList);
  if (!available.has(endWord)) return 0;
  available.delete(beginWord);
  available.delete(endWord);
  // Two frontiers grow toward each other; words counts the ladder length covered so far.
  let near = new Set([beginWord]);
  let far = new Set([endWord]);
  let words = 1;
  while (near.size > 0 && far.size > 0) {
    if (near.size > far.size) [near, far] = [far, near]; // always expand the smaller frontier
    words++;
    const next = new Set<string>();
    for (const word of near) {
      for (let position = 0; position < word.length; position++) {
        const prefix = word.slice(0, position);
        const suffix = word.slice(position + 1);
        for (const letter of LETTERS) {
          const candidate = prefix + letter + suffix;
          if (far.has(candidate)) return words;
          if (available.delete(candidate)) next.add(candidate);
        }
      }
    }
    near = next;
  }
  return 0;
}
