const ALPHABET = 26;
const FIRST_LETTER = "a".charCodeAt(0);

class TrieNode {
  readonly children: (TrieNode | null)[] = new Array<TrieNode | null>(ALPHABET).fill(null);
  end = false; // a root ends at this node
}

export function replaceWords(dictionary: string[], sentence: string): string {
  const trie = new TrieNode();
  for (const root of dictionary) {
    let node = trie;
    for (let i = 0; i < root.length; i++) {
      const letter = root.charCodeAt(i) - FIRST_LETTER;
      let child = node.children[letter];
      if (child === null) {
        child = new TrieNode();
        node.children[letter] = child;
      }
      node = child;
    }
    node.end = true;
  }
  return sentence
    .split(" ")
    .map((word) => shorten(trie, word))
    .join(" ");
}

function shorten(trie: TrieNode, word: string): string {
  let node = trie;
  for (let length = 0; length < word.length; length++) {
    if (node.end) {
      return word.slice(0, length);
    }
    const next = node.children[word.charCodeAt(length) - FIRST_LETTER];
    if (next === null) {
      return word;
    }
    node = next;
  }
  return word;
}
