import { TreeNode } from "#support";

export function lowestCommonAncestor(root: TreeNode, p: TreeNode, q: TreeNode): TreeNode {
  // Map keys compare objects by identity.
  const parent = new Map<TreeNode, TreeNode | null>([[root, null]]);
  const pending: TreeNode[] = [root];
  while (!parent.has(p) || !parent.has(q)) {
    const node = pending.pop()!;
    for (const child of [node.left, node.right]) {
      if (child !== null) {
        parent.set(child, node);
        pending.push(child);
      }
    }
  }
  const ancestorsOfP = new Set<TreeNode>();
  for (let node: TreeNode | null = p; node !== null; node = parent.get(node)!) {
    ancestorsOfP.add(node);
  }
  let node = q;
  while (!ancestorsOfP.has(node)) {
    node = parent.get(node)!;
  }
  return node;
}
