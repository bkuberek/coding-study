import cs.support.*;
import java.util.*;

public class Solution {
    public GraphNode cloneGraph(GraphNode node) {
        if (node == null) {
            return null;
        }
        Map<GraphNode, GraphNode> clones = new HashMap<>();
        clones.put(node, new GraphNode(node.val));
        Queue<GraphNode> queue = new ArrayDeque<>();
        queue.add(node);
        while (!queue.isEmpty()) {
            GraphNode original = queue.poll();
            GraphNode clone = clones.get(original);
            for (GraphNode neighbor : original.neighbors) {
                GraphNode neighborClone = clones.get(neighbor);
                if (neighborClone == null) {
                    neighborClone = new GraphNode(neighbor.val);
                    clones.put(neighbor, neighborClone);
                    queue.add(neighbor);
                }
                clone.neighbors.add(neighborClone);
            }
        }
        return clones.get(node);
    }
}
