import { TreeNode } from "#support";

export function isValidBST(root: TreeNode | null): boolean {
  const stack: TreeNode[] = [];
  let node = root;
  let previous = -Infinity;
  while (stack.length > 0 || node !== null) {
    while (node !== null) {
      stack.push(node);
      node = node.left;
    }
    const current = stack.pop()!;
    if (current.val <= previous) {
      return false;
    }
    previous = current.val;
    node = current.right;
  }
  return true;
}
