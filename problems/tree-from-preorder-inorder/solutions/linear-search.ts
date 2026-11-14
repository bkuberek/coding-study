import { TreeNode } from "#support";

export function buildTree(preorder: number[], inorder: number[]): TreeNode | null {
  /** Tree of the `size` values starting at preorder[preStart] and inorder[inStart]. */
  const build = (preStart: number, inStart: number, size: number): TreeNode | null => {
    if (size === 0) return null;
    const value = preorder[preStart];
    let split = inStart;
    while (inorder[split] !== value) split++;
    const leftSize = split - inStart;
    const node = new TreeNode(value);
    node.left = build(preStart + 1, inStart, leftSize);
    node.right = build(preStart + 1 + leftSize, split + 1, size - leftSize - 1);
    return node;
  };
  return build(0, 0, preorder.length);
}
