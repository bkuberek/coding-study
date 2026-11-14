const ALPHABET_SIZE = 26;
const CODE_OF_A = "a".charCodeAt(0);

class TrieNode {
  readonly children: (TrieNode | null)[] = new Array(ALPHABET_SIZE).fill(null);
  passing = 0; // how many words go through this node
}

export function countByPrefix(words: string[], prefixes: string[]): number[] {
  const root = new TrieNode();
  for (const word of words) {
    let node = root;
    for (let i = 0; i < word.length; i++) {
      node = node.children[word.charCodeAt(i) - CODE_OF_A] ??= new TrieNode();
      node.passing++;
    }
  }

  return prefixes.map((prefix) => {
    let node: TrieNode | null = root;
    for (let i = 0; i < prefix.length && node !== null; i++) {
      node = node.children[prefix.charCodeAt(i) - CODE_OF_A];
    }
    // A broken path leaves null: no word begins with this prefix.
    return node === null ? 0 : node.passing;
  });
}
