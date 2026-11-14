import { TreeNode } from "#support";

export function maxDepth(root: TreeNode | null): number {
  let level: TreeNode[] = root === null ? [] : [root];
  let depth = 0;
  while (level.length > 0) {
    depth++;
    const next: TreeNode[] = [];
    for (const node of level) {
      if (node.left !== null) next.push(node.left);
      if (node.right !== null) next.push(node.right);
    }
    level = next;
  }
  return depth;
}
