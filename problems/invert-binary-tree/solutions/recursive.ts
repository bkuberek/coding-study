import { TreeNode } from "#support";

export function invertTree(root: TreeNode | null): TreeNode | null {
  if (root === null) {
    return null;
  }
  const invertedLeft = invertTree(root.left);
  root.left = invertTree(root.right);
  root.right = invertedLeft;
  return root;
}
