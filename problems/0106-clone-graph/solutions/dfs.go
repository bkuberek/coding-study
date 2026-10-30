package clone_graph

import "cstudy/support"

type GraphNode = support.GraphNode

func cloneGraph(node *GraphNode) *GraphNode {
	if node == nil {
		return nil
	}
	clones := make(map[*GraphNode]*GraphNode)

	var copyNode func(original *GraphNode) *GraphNode
	copyNode = func(original *GraphNode) *GraphNode {
		if clone, ok := clones[original]; ok {
			return clone
		}
		// Register the copy before visiting neighbors: a cycle leads back here and must
		// find this copy instead of starting a second one.
		clone := &GraphNode{Val: original.Val}
		clones[original] = clone
		for _, neighbor := range original.Neighbors {
			clone.Neighbors = append(clone.Neighbors, copyNode(neighbor))
		}
		return clone
	}

	return copyNode(node)
}
