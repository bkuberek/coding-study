import { TreeNode } from "#support";

export function pathSum(root: TreeNode | null, targetSum: number): number {
  // onPath maps a prefix sum of the current root path to how many prefixes have it.
  const onPath = new Map<number, number>([[0, 1]]);

  function countBelow(node: TreeNode | null, total: number): number {
    if (node === null) {
      return 0;
    }
    total += node.val;
    let found = onPath.get(total - targetSum) ?? 0;
    onPath.set(total, (onPath.get(total) ?? 0) + 1);
    found += countBelow(node.left, total) + countBelow(node.right, total);
    onPath.set(total, onPath.get(total)! - 1); // leave the subtree
    return found;
  }

  return countBelow(root, 0);
}
