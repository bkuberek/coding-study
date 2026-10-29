package vertical_order_traversal

import (
	"cmp"
	"slices"

	"cstudy/support"
)

type TreeNode = support.TreeNode

func verticalOrder(root *TreeNode) [][]int {
	type entry struct{ column, row, value int }
	var entries []entry // in pre-order
	var visit func(node *TreeNode, column, row int)
	visit = func(node *TreeNode, column, row int) {
		if node == nil {
			return
		}
		entries = append(entries, entry{column, row, node.Val})
		visit(node.Left, column-1, row+1)
		visit(node.Right, column+1, row+1)
	}
	visit(root, 0, 0)
	// A stable sort keeps pre-order (left to right) among nodes with the same column and row.
	slices.SortStableFunc(entries, func(a, b entry) int {
		return cmp.Or(cmp.Compare(a.column, b.column), cmp.Compare(a.row, b.row))
	})
	var columns [][]int
	for i, e := range entries {
		if i == 0 || e.column != entries[i-1].column {
			columns = append(columns, nil)
		}
		last := len(columns) - 1
		columns[last] = append(columns[last], e.value)
	}
	return columns
}
