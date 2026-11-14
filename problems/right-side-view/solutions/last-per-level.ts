import { TreeNode } from "#support";

export function rightSideView(root: TreeNode | null): number[] {
  const view: number[] = [];
  let level: TreeNode[] = root === null ? [] : [root];
  while (level.length > 0) {
    view.push(level[level.length - 1].val);
    const next: TreeNode[] = [];
    for (const node of level) {
      if (node.left !== null) next.push(node.left);
      if (node.right !== null) next.push(node.right);
    }
    level = next;
  }
  return view;
}
