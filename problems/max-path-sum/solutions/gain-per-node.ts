import { TreeNode } from "#support";

export function maxPathSum(root: TreeNode | null): number {
  const node = root!;
  let best = node.val + Math.max(0, gain(node.left)) + Math.max(0, gain(node.right));
  for (const child of [node.left, node.right]) {
    if (child !== null) best = Math.max(best, maxPathSum(child));
  }
  return best;
}

/** Largest sum of a path that starts at `node` and only goes down (0 for no node). */
function gain(node: TreeNode | null): number {
  return node === null ? 0 : node.val + Math.max(0, gain(node.left), gain(node.right));
}
