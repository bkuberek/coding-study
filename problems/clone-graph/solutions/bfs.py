from collections import deque

from cs_support import GraphNode


def clone_graph(node: GraphNode | None) -> GraphNode | None:
    if node is None:
        return None
    clones = {node: GraphNode(node.val)}
    queue = deque([node])
    while queue:
        original = queue.popleft()
        clone = clones[original]
        for neighbor in original.neighbors:
            if neighbor not in clones:
                clones[neighbor] = GraphNode(neighbor.val)
                queue.append(neighbor)
            clone.neighbors.append(clones[neighbor])
    return clones[node]
