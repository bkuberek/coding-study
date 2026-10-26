export class WordDictionary {
  private readonly byLength = new Map<number, Set<string>>();

  addWord(word: string): void {
    let bucket = this.byLength.get(word.length);
    if (bucket === undefined) {
      bucket = new Set<string>();
      this.byLength.set(word.length, bucket);
    }
    bucket.add(word);
  }

  search(word: string): boolean {
    const candidates = this.byLength.get(word.length);
    if (candidates === undefined) return false;
    if (!word.includes(".")) return candidates.has(word);
    for (const candidate of candidates) {
      if (matches(word, candidate)) return true;
    }
    return false;
  }
}

function matches(pattern: string, word: string): boolean {
  for (let i = 0; i < pattern.length; i++) {
    if (pattern[i] !== "." && pattern[i] !== word[i]) return false;
  }
  return true;
}
