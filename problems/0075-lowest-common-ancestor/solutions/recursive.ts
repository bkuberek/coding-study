import { TreeNode } from "#support";

/** The answer if both p and q are below `root`, else whichever of them is below, else null. */
export function lowestCommonAncestor(root: TreeNode | null, p: TreeNode, q: TreeNode): TreeNode | null {
  if (root === null || root === p || root === q) {
    return root;
  }
  const left = lowestCommonAncestor(root.left, p, q);
  const right = lowestCommonAncestor(root.right, p, q);
  if (left !== null && right !== null) {
    return root;
  }
  return left ?? right;
}
