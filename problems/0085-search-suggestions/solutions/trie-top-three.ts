const ALPHABET_SIZE = 26;
const SHOWN = 3;
const CODE_OF_A = "a".charCodeAt(0);

class TrieNode {
  readonly children: (TrieNode | null)[] = new Array(ALPHABET_SIZE).fill(null);
  readonly smallest: string[] = [];
}

export function suggestedProducts(products: string[], searchWord: string): string[][] {
  const root = new TrieNode();
  // Inserting in sorted order means each node's first three products are its smallest.
  for (const product of [...products].sort()) {
    let node = root;
    for (let i = 0; i < product.length; i++) {
      node = node.children[product.charCodeAt(i) - CODE_OF_A] ??= new TrieNode();
      if (node.smallest.length < SHOWN) node.smallest.push(product);
    }
  }
  const suggestions: string[][] = [];
  let node: TrieNode | null = root;
  for (let i = 0; i < searchWord.length; i++) {
    node = node === null ? null : node.children[searchWord.charCodeAt(i) - CODE_OF_A];
    suggestions.push(node === null ? [] : [...node.smallest]);
  }
  return suggestions;
}
