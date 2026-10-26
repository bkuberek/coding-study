import { TreeNode } from "#support";

export function isValidBST(root: TreeNode | null): boolean {
  return within(root, -Infinity, Infinity);
}

/** Is every value of the subtree strictly between `low` and `high`? */
function within(node: TreeNode | null, low: number, high: number): boolean {
  if (node === null) {
    return true;
  }
  if (node.val <= low || node.val >= high) {
    return false;
  }
  return within(node.left, low, node.val) && within(node.right, node.val, high);
}
