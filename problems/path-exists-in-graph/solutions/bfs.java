import java.util.*;

public class Solution {
    public boolean hasPath(int n, int[][] edges, int source, int target) {
        // neighbors.get(node) lists every node joined to `node`; each connection works both ways.
        List<List<Integer>> neighbors = new ArrayList<>();
        for (int node = 0; node < n; node++) {
            neighbors.add(new ArrayList<>());
        }
        for (int[] edge : edges) {
            neighbors.get(edge[0]).add(edge[1]);
            neighbors.get(edge[1]).add(edge[0]);
        }
        boolean[] seen = new boolean[n];
        seen[source] = true;
        Queue<Integer> queue = new ArrayDeque<>();
        queue.add(source);
        while (!queue.isEmpty()) {
            int node = queue.poll();
            if (node == target) {
                return true;
            }
            for (int neighbor : neighbors.get(node)) {
                if (!seen[neighbor]) {
                    seen[neighbor] = true;
                    queue.add(neighbor);
                }
            }
        }
        return false;
    }
}
