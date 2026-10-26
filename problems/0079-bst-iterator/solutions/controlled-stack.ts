import { TreeNode } from "#support";

export class BSTIterator {
  // Nodes whose left subtree is finished (or about to be) and that are not returned yet.
  private readonly stack: TreeNode[] = [];

  constructor(root: TreeNode | null) {
    this.pushLeftSpine(root);
  }

  private pushLeftSpine(node: TreeNode | null): void {
    for (let current = node; current !== null; current = current.left) {
      this.stack.push(current);
    }
  }

  next(): number {
    const node = this.stack.pop()!;
    this.pushLeftSpine(node.right);
    return node.val;
  }

  hasNext(): boolean {
    return this.stack.length > 0;
  }
}
