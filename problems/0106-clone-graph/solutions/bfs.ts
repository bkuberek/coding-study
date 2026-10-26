import { GraphNode } from "#support";

export function cloneGraph(node: GraphNode | null): GraphNode | null {
  if (node === null) return null;
  const clones = new Map<GraphNode, GraphNode>([[node, new GraphNode(node.val)]]);
  const queue: GraphNode[] = [node];
  // A moving head index instead of Array.shift(), which is O(n) per call.
  for (let head = 0; head < queue.length; head++) {
    const original = queue[head];
    const clone = clones.get(original)!;
    for (const neighbor of original.neighbors) {
      let neighborClone = clones.get(neighbor);
      if (neighborClone === undefined) {
        neighborClone = new GraphNode(neighbor.val);
        clones.set(neighbor, neighborClone);
        queue.push(neighbor);
      }
      clone.neighbors.push(neighborClone);
    }
  }
  return clones.get(node)!;
}
