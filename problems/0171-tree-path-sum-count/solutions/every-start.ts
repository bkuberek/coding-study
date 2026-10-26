import { TreeNode } from "#support";

export function pathSum(root: TreeNode | null, targetSum: number): number {
  let count = 0;
  const starts: TreeNode[] = root === null ? [] : [root];
  while (starts.length > 0) {
    const start = starts.pop()!;
    // Walk every downward path from start, carrying the sum so far.
    const nodes: TreeNode[] = [start];
    const totals: number[] = [start.val];
    while (nodes.length > 0) {
      const node = nodes.pop()!;
      const total = totals.pop()!;
      if (total === targetSum) {
        count++;
      }
      for (const child of [node.left, node.right]) {
        if (child !== null) {
          nodes.push(child);
          totals.push(total + child.val);
        }
      }
    }
    if (start.left !== null) starts.push(start.left);
    if (start.right !== null) starts.push(start.right);
  }
  return count;
}
