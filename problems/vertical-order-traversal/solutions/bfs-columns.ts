import { TreeNode } from "#support";

export function verticalOrder(root: TreeNode | null): number[][] {
  if (root === null) {
    return [];
  }
  const columns = new Map<number, number[]>();
  let leftmost = 0;
  let rightmost = 0;
  const nodes: TreeNode[] = [root];
  const columnOf: number[] = [0];
  // A read index instead of Array.shift(), which is linear on large arrays.
  for (let head = 0; head < nodes.length; head++) {
    const node = nodes[head];
    const column = columnOf[head];
    const bucket = columns.get(column);
    if (bucket === undefined) columns.set(column, [node.val]);
    else bucket.push(node.val);
    leftmost = Math.min(leftmost, column);
    rightmost = Math.max(rightmost, column);
    if (node.left !== null) {
      nodes.push(node.left);
      columnOf.push(column - 1);
    }
    if (node.right !== null) {
      nodes.push(node.right);
      columnOf.push(column + 1);
    }
  }
  const result: number[][] = [];
  for (let column = leftmost; column <= rightmost; column++) result.push(columns.get(column)!);
  return result;
}
