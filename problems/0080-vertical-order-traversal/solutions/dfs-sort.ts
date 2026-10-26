import { TreeNode } from "#support";

type Entry = { column: number; row: number; value: number };

export function verticalOrder(root: TreeNode | null): number[][] {
  const entries: Entry[] = [];
  const visit = (node: TreeNode | null, column: number, row: number): void => {
    if (node === null) return;
    entries.push({ column, row, value: node.val });
    visit(node.left, column - 1, row + 1);
    visit(node.right, column + 1, row + 1);
  };
  visit(root, 0, 0);
  // Array.prototype.sort is stable, so pre-order (left to right) survives among ties.
  entries.sort((a, b) => a.column - b.column || a.row - b.row);
  const columns: number[][] = [];
  entries.forEach((entry, i) => {
    if (i === 0 || entry.column !== entries[i - 1].column) columns.push([]);
    columns[columns.length - 1].push(entry.value);
  });
  return columns;
}
