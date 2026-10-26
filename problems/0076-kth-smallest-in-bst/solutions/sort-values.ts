import { TreeNode } from "#support";

export function kthSmallest(root: TreeNode | null, k: number): number {
  const values: number[] = [];
  const pending: (TreeNode | null)[] = [root];
  while (pending.length > 0) {
    const node = pending.pop()!;
    if (node !== null) {
      values.push(node.val);
      pending.push(node.left, node.right);
    }
  }
  // Without a comparator, sort() would order the numbers as strings.
  values.sort((a, b) => a - b);
  return values[k - 1];
}
