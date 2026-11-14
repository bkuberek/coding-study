import java.util.*;

public class Solution {
    private List<List<Integer>> adjacency;
    // discovered[v] is the order in which v was first reached (-1: not yet).
    // low[v] is the earliest discovery time reachable from v's subtree using at most one
    // cable that is not a tree edge.
    private int[] discovered;
    private int[] low;
    private int clock;
    private List<List<Integer>> bridges;

    public List<List<Integer>> criticalConnections(int n, int[][] connections) {
        adjacency = new ArrayList<>();
        for (int server = 0; server < n; server++) {
            adjacency.add(new ArrayList<>());
        }
        for (int[] cable : connections) {
            adjacency.get(cable[0]).add(cable[1]);
            adjacency.get(cable[1]).add(cable[0]);
        }
        discovered = new int[n];
        Arrays.fill(discovered, -1);
        low = new int[n];
        clock = 0;
        bridges = new ArrayList<>();
        visit(0, -1);
        return bridges;
    }

    private void visit(int server, int parent) {
        discovered[server] = low[server] = clock++;
        for (int neighbor : adjacency.get(server)) {
            if (neighbor == parent) {
                continue; // the tree edge we arrived by is not a way back
            }
            if (discovered[neighbor] == -1) {
                visit(neighbor, server);
                low[server] = Math.min(low[server], low[neighbor]);
                if (low[neighbor] > discovered[server]) {
                    bridges.add(List.of(server, neighbor));
                }
            } else {
                low[server] = Math.min(low[server], discovered[neighbor]);
            }
        }
    }
}
