import { TreeNode } from "#support";

export function isBalanced(root: TreeNode | null): boolean {
  if (root === null) {
    return true;
  }
  return (
    Math.abs(height(root.left) - height(root.right)) <= 1 && isBalanced(root.left) && isBalanced(root.right)
  );
}

function height(node: TreeNode | null): number {
  return node === null ? 0 : 1 + Math.max(height(node.left), height(node.right));
}
