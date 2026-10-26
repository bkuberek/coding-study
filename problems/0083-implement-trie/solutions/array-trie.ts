const ALPHABET_SIZE = 26;
const CODE_OF_A = "a".charCodeAt(0);

class TrieNode {
  readonly children: (TrieNode | null)[] = new Array(ALPHABET_SIZE).fill(null);
  isWord = false;
}

export class Trie {
  private readonly root = new TrieNode();

  insert(word: string): void {
    let node = this.root;
    for (let i = 0; i < word.length; i++) {
      const index = word.charCodeAt(i) - CODE_OF_A;
      node = node.children[index] ??= new TrieNode();
    }
    node.isWord = true;
  }

  search(word: string): boolean {
    return this.walk(word)?.isWord ?? false;
  }

  startsWith(prefix: string): boolean {
    return this.walk(prefix) !== null;
  }

  /** The node at the end of the path spelled by `text`, or null if the path breaks off. */
  private walk(text: string): TrieNode | null {
    let node: TrieNode | null = this.root;
    for (let i = 0; i < text.length && node !== null; i++) {
      node = node.children[text.charCodeAt(i) - CODE_OF_A];
    }
    return node;
  }
}
