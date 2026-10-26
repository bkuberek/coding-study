import { TreeNode } from "#support";

export function levelOrder(root: TreeNode | null): number[][] {
  const levels: number[][] = [];
  const visit = (node: TreeNode | null, depth: number): void => {
    if (node === null) return;
    if (depth === levels.length) levels.push([]);
    levels[depth].push(node.val);
    visit(node.left, depth + 1);
    visit(node.right, depth + 1);
  };
  visit(root, 0);
  return levels;
}
