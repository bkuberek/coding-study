package cs.support;

import java.util.ArrayList;
import java.util.List;

/** An undirected graph node. JSON: a 1-indexed adjacency list where node {@code i} has val i. */
public class GraphNode {
    public int val;
    public List<GraphNode> neighbors;

    public GraphNode() {
        this.neighbors = new ArrayList<>();
    }

    public GraphNode(int val) {
        this.val = val;
        this.neighbors = new ArrayList<>();
    }

    public GraphNode(int val, List<GraphNode> neighbors) {
        this.val = val;
        this.neighbors = neighbors;
    }
}
