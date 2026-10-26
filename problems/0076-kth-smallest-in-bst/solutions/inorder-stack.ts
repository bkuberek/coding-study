import { TreeNode } from "#support";

export function kthSmallest(root: TreeNode | null, k: number): number {
  const stack: TreeNode[] = [];
  let node = root;
  let remaining = k;
  for (;;) {
    while (node !== null) {
      stack.push(node);
      node = node.left;
    }
    const current = stack.pop()!;
    remaining--;
    if (remaining === 0) {
      return current.val;
    }
    node = current.right;
  }
}
