import { TreeNode } from "#support";

export function levelOrder(root: TreeNode | null): number[][] {
  const levels: number[][] = [];
  let current: TreeNode[] = root === null ? [] : [root];
  while (current.length > 0) {
    levels.push(current.map((node) => node.val));
    const next: TreeNode[] = [];
    for (const node of current) {
      if (node.left !== null) next.push(node.left);
      if (node.right !== null) next.push(node.right);
    }
    current = next;
  }
  return levels;
}
