package vertical_order_traversal

import "cstudy/support"

type TreeNode = support.TreeNode

func verticalOrder(root *TreeNode) [][]int {
	if root == nil {
		return nil
	}
	type entry struct {
		node   *TreeNode
		column int
	}
	columns := make(map[int][]int)
	lowest, highest := 0, 0
	queue := []entry{{root, 0}}
	for len(queue) > 0 {
		head := queue[0]
		queue = queue[1:]
		columns[head.column] = append(columns[head.column], head.node.Val)
		lowest, highest = min(lowest, head.column), max(highest, head.column)
		if head.node.Left != nil {
			queue = append(queue, entry{head.node.Left, head.column - 1})
		}
		if head.node.Right != nil {
			queue = append(queue, entry{head.node.Right, head.column + 1})
		}
	}
	// Columns form a contiguous range: every path from the root moves one column per step.
	result := make([][]int, 0, highest-lowest+1)
	for column := lowest; column <= highest; column++ {
		result = append(result, columns[column])
	}
	return result
}
