export class Trie {
  private readonly words = new Set<string>();

  insert(word: string): void {
    this.words.add(word);
  }

  search(word: string): boolean {
    return this.words.has(word);
  }

  startsWith(prefix: string): boolean {
    for (const word of this.words) {
      if (word.startsWith(prefix)) return true;
    }
    return false;
  }
}
