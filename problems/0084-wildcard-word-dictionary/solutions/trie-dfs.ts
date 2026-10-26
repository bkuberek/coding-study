const ALPHABET_SIZE = 26;
const CODE_OF_A = "a".charCodeAt(0);

class TrieNode {
  readonly children: (TrieNode | null)[] = new Array(ALPHABET_SIZE).fill(null);
  isWord = false;
}

export class WordDictionary {
  private readonly root = new TrieNode();

  addWord(word: string): void {
    let node = this.root;
    for (let i = 0; i < word.length; i++) {
      node = node.children[word.charCodeAt(i) - CODE_OF_A] ??= new TrieNode();
    }
    node.isWord = true;
  }

  search(word: string): boolean {
    /** Does some stored word continue from `start` the way word[position..] says? */
    const matchesFrom = (start: TrieNode, position: number): boolean => {
      let node = start;
      for (let at = position; at < word.length; at++) {
        if (word[at] === ".") {
          return node.children.some((child) => child !== null && matchesFrom(child, at + 1));
        }
        const child = node.children[word.charCodeAt(at) - CODE_OF_A];
        if (child === null) return false;
        node = child;
      }
      return node.isWord;
    };
    return matchesFrom(this.root, 0);
  }
}
