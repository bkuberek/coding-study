package clone_graph

import "cstudy/support"

type GraphNode = support.GraphNode

func cloneGraph(node *GraphNode) *GraphNode {
	if node == nil {
		return nil
	}
	clones := map[*GraphNode]*GraphNode{node: {Val: node.Val}}
	queue := []*GraphNode{node}
	for len(queue) > 0 {
		original := queue[0]
		queue = queue[1:]
		clone := clones[original]
		for _, neighbor := range original.Neighbors {
			if _, seen := clones[neighbor]; !seen {
				clones[neighbor] = &GraphNode{Val: neighbor.Val}
				queue = append(queue, neighbor)
			}
			clone.Neighbors = append(clone.Neighbors, clones[neighbor])
		}
	}
	return clones[node]
}
