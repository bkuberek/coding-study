import cs.support.*;
import java.util.*;

public class Solution {
    public GraphNode cloneGraph(GraphNode node) {
        return node == null ? null : copy(node, new HashMap<>());
    }

    private GraphNode copy(GraphNode original, Map<GraphNode, GraphNode> clones) {
        GraphNode known = clones.get(original);
        if (known != null) {
            return known;
        }
        // Register the copy before recursing, so a cycle back to this node finds it.
        GraphNode clone = new GraphNode(original.val);
        clones.put(original, clone);
        for (GraphNode neighbor : original.neighbors) {
            clone.neighbors.add(copy(neighbor, clones));
        }
        return clone;
    }
}
