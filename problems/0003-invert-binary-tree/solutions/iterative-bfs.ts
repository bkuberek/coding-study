import { TreeNode } from "#support";

export function invertTree(root: TreeNode | null): TreeNode | null {
  const pending: TreeNode[] = root === null ? [] : [root];
  // A read index instead of Array.shift(), which is O(n) per call on large arrays.
  for (let head = 0; head < pending.length; head++) {
    const node = pending[head];
    [node.left, node.right] = [node.right, node.left];
    if (node.left !== null) pending.push(node.left);
    if (node.right !== null) pending.push(node.right);
  }
  return root;
}
