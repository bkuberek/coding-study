import { TreeNode } from "#support";

export class BSTIterator {
  private readonly values: number[] = [];
  private position = 0;

  constructor(root: TreeNode | null) {
    this.collect(root);
  }

  private collect(node: TreeNode | null): void {
    if (node === null) return;
    this.collect(node.left);
    this.values.push(node.val);
    this.collect(node.right);
  }

  next(): number {
    return this.values[this.position++];
  }

  hasNext(): boolean {
    return this.position < this.values.length;
  }
}
