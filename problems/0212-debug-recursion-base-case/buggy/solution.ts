// Debug: Recursion Base Case. Some tests fail: find the bug and fix it.
import { TreeNode } from "#support";

export function hasPathSum(root: TreeNode | null, target: number): boolean {
  if (root === null) {
    return target === 0;
  }
  const remaining = target - root.val;
  return hasPathSum(root.left, remaining) || hasPathSum(root.right, remaining);
}
