import { TreeNode } from "#support";

export function rightSideView(root: TreeNode | null): number[] {
  const view: number[] = [];
  const visit = (node: TreeNode | null, depth: number): void => {
    if (node === null) return;
    if (depth === view.length) view.push(node.val);
    visit(node.right, depth + 1);
    visit(node.left, depth + 1);
  };
  visit(root, 0);
  return view;
}
