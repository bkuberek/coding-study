import { TreeNode } from "#support";

// Values lie in [-10^4, 10^4], so this marker for a missing child never equals a value.
const NO_NODE = 1_000_000;

export function isSubtree(root: TreeNode | null, subRoot: TreeNode | null): boolean {
  return occurs(tokens(subRoot), tokens(root));
}

/** Pre-order values with NO_NODE for every missing child: a unique description of the tree. */
function tokens(root: TreeNode | null): number[] {
  const out: number[] = [];
  const pending: (TreeNode | null)[] = [root];
  while (pending.length > 0) {
    const node = pending.pop()!;
    if (node === null) {
      out.push(NO_NODE);
      continue;
    }
    out.push(node.val);
    pending.push(node.right, node.left);
  }
  return out;
}

/** Knuth-Morris-Pratt: does `pattern` occur as a contiguous block of `text`? */
function occurs(pattern: number[], text: number[]): boolean {
  const border = new Array<number>(pattern.length).fill(0);
  let length = 0;
  for (let i = 1; i < pattern.length; i++) {
    while (length > 0 && pattern[i] !== pattern[length]) length = border[length - 1];
    if (pattern[i] === pattern[length]) length++;
    border[i] = length;
  }
  let matched = 0;
  for (const token of text) {
    while (matched > 0 && token !== pattern[matched]) matched = border[matched - 1];
    if (token === pattern[matched]) {
      matched++;
      if (matched === pattern.length) return true;
    }
  }
  return false;
}
