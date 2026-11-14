import { TreeNode } from "#support";

export function isSubtree(root: TreeNode | null, subRoot: TreeNode | null): boolean {
  if (root === null) {
    return false;
  }
  return same(root, subRoot) || isSubtree(root.left, subRoot) || isSubtree(root.right, subRoot);
}

function same(a: TreeNode | null, b: TreeNode | null): boolean {
  if (a === null || b === null) {
    return a === b;
  }
  return a.val === b.val && same(a.left, b.left) && same(a.right, b.right);
}
