import { TreeNode } from "#support";

export function isSameTree(p: TreeNode | null, q: TreeNode | null): boolean {
  const pending: [TreeNode | null, TreeNode | null][] = [[p, q]];
  while (pending.length > 0) {
    const [a, b] = pending.pop()!;
    if (a === null && b === null) continue;
    if (a === null || b === null || a.val !== b.val) return false;
    pending.push([a.right, b.right], [a.left, b.left]);
  }
  return true;
}
