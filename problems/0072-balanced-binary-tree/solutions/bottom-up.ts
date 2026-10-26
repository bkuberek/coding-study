import { TreeNode } from "#support";

const UNBALANCED = -1;

export function isBalanced(root: TreeNode | null): boolean {
  return checkedHeight(root) !== UNBALANCED;
}

/** Height of `node`, or UNBALANCED as soon as any subtree below it is unbalanced. */
function checkedHeight(node: TreeNode | null): number {
  if (node === null) {
    return 0;
  }
  const left = checkedHeight(node.left);
  if (left === UNBALANCED) {
    return UNBALANCED;
  }
  const right = checkedHeight(node.right);
  if (right === UNBALANCED || Math.abs(left - right) > 1) {
    return UNBALANCED;
  }
  return 1 + Math.max(left, right);
}
