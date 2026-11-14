from cs_support import GraphNode


def clone_graph(node: GraphNode | None) -> GraphNode | None:
    clones: dict[GraphNode, GraphNode] = {}

    def copy(original: GraphNode) -> GraphNode:
        if original in clones:
            return clones[original]
        # Register the copy before visiting neighbors: a cycle leads back here and must
        # find this copy instead of starting a second one.
        clone = GraphNode(original.val)
        clones[original] = clone
        clone.neighbors = [copy(neighbor) for neighbor in original.neighbors]
        return clone

    return copy(node) if node is not None else None
