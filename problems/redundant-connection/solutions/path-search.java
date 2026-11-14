import java.util.*;

public class Solution {
    public int[] findRedundantConnection(int[][] edges) {
        List<List<Integer>> neighbors = new ArrayList<>(edges.length + 1);
        for (int node = 0; node <= edges.length; node++) {
            neighbors.add(new ArrayList<>());
        }
        for (int[] edge : edges) {
            // The first edge whose ends are already connected closes the only cycle.
            if (connected(neighbors, edge[0], edge[1])) {
                return edge;
            }
            neighbors.get(edge[0]).add(edge[1]);
            neighbors.get(edge[1]).add(edge[0]);
        }
        return new int[0];
    }

    private static boolean connected(List<List<Integer>> neighbors, int start, int goal) {
        boolean[] seen = new boolean[neighbors.size()];
        ArrayDeque<Integer> stack = new ArrayDeque<>();
        seen[start] = true;
        stack.push(start);
        while (!stack.isEmpty()) {
            int node = stack.pop();
            if (node == goal) {
                return true;
            }
            for (int neighbor : neighbors.get(node)) {
                if (!seen[neighbor]) {
                    seen[neighbor] = true;
                    stack.push(neighbor);
                }
            }
        }
        return false;
    }
}
