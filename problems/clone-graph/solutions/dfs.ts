import { GraphNode } from "#support";

export function cloneGraph(node: GraphNode | null): GraphNode | null {
  const clones = new Map<GraphNode, GraphNode>();
  const copy = (original: GraphNode): GraphNode => {
    const known = clones.get(original);
    if (known !== undefined) return known;
    // Register the copy before recursing, so a cycle back to this node finds it.
    const clone = new GraphNode(original.val);
    clones.set(original, clone);
    for (const neighbor of original.neighbors) {
      clone.neighbors.push(copy(neighbor));
    }
    return clone;
  };
  return node === null ? null : copy(node);
}
