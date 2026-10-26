import { TreeNode } from "#support";

export function diameterOfBinaryTree(root: TreeNode | null): number {
  if (root === null) {
    return 0;
  }
  const turningHere = height(root.left) + height(root.right);
  return Math.max(turningHere, diameterOfBinaryTree(root.left), diameterOfBinaryTree(root.right));
}

/** Number of nodes on the longest downward path from `node`. */
function height(node: TreeNode | null): number {
  return node === null ? 0 : 1 + Math.max(height(node.left), height(node.right));
}
