import { TreeNode } from "#support";

export function isValidBST(root: TreeNode | null): boolean {
  if (root === null) {
    return true;
  }
  if (root.left !== null && largest(root.left) >= root.val) return false;
  if (root.right !== null && smallest(root.right) <= root.val) return false;
  return isValidBST(root.left) && isValidBST(root.right);
}

/** Largest value anywhere in the subtree; it need not be a search tree, so scan it all. */
function largest(node: TreeNode | null): number {
  return node === null ? -Infinity : Math.max(node.val, largest(node.left), largest(node.right));
}

function smallest(node: TreeNode | null): number {
  return node === null ? Infinity : Math.min(node.val, smallest(node.left), smallest(node.right));
}
