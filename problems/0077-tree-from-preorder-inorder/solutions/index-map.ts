import { TreeNode } from "#support";

export function buildTree(preorder: number[], inorder: number[]): TreeNode | null {
  const position = new Map<number, number>();
  inorder.forEach((value, index) => position.set(value, index));
  let nextRoot = 0;
  /** Tree whose in-order walk is inorder[low, high); its root is the next pre-order value. */
  const build = (low: number, high: number): TreeNode | null => {
    if (low === high) return null;
    const value = preorder[nextRoot++];
    const split = position.get(value)!;
    const node = new TreeNode(value);
    node.left = build(low, split);
    node.right = build(split + 1, high);
    return node;
  };
  return build(0, inorder.length);
}
