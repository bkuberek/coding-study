import { TreeNode } from "#support";

export function hasPathSum(root: TreeNode | null, target: number): boolean {
  if (root === null) {
    return false;
  }
  const remaining = target - root.val;
  if (root.left === null && root.right === null) {
    return remaining === 0;
  }
  return hasPathSum(root.left, remaining) || hasPathSum(root.right, remaining);
}
