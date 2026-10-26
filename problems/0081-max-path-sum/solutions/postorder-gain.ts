import { TreeNode } from "#support";

export function maxPathSum(root: TreeNode | null): number {
  let best = root!.val;
  /** Best downward path sum from `node`, recording the best path turning at it. */
  const gain = (node: TreeNode | null): number => {
    if (node === null) return 0;
    const left = Math.max(0, gain(node.left));
    const right = Math.max(0, gain(node.right));
    best = Math.max(best, node.val + left + right);
    return node.val + Math.max(left, right);
  };
  gain(root);
  return best;
}
