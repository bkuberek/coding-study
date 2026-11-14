type TrieNode = { children: Map<string, TrieNode>; endsWord: boolean };

function newNode(): TrieNode {
  return { children: new Map(), endsWord: false };
}

export function wordBreak(s: string, wordDict: string[]): boolean {
  const root = newNode();
  for (const word of wordDict) {
    let node = root;
    for (const letter of word) {
      let child = node.children.get(letter);
      if (child === undefined) {
        child = newNode();
        node.children.set(letter, child);
      }
      node = child;
    }
    node.endsWord = true;
  }

  // reachable[i] is true when the prefix s[0..i) can be split into dictionary words.
  const reachable = new Array<boolean>(s.length + 1).fill(false);
  reachable[0] = true;
  for (let start = 0; start < s.length; start++) {
    if (!reachable[start]) {
      continue;
    }
    let node: TrieNode | undefined = root;
    for (let position = start; position < s.length; position++) {
      node = node.children.get(s[position]);
      if (node === undefined) {
        break;
      }
      if (node.endsWord) {
        reachable[position + 1] = true;
      }
    }
  }
  return reachable[s.length];
}
