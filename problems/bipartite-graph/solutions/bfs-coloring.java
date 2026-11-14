import java.util.*;

public class Solution {
    private static final int UNCOLORED = -1;

    public boolean isBipartite(int[][] graph) {
        int[] color = new int[graph.length];
        Arrays.fill(color, UNCOLORED);
        Queue<Integer> queue = new ArrayDeque<>();
        // Every piece of the graph needs its own start node.
        for (int start = 0; start < graph.length; start++) {
            if (color[start] != UNCOLORED) {
                continue;
            }
            color[start] = 0;
            queue.add(start);
            while (!queue.isEmpty()) {
                int node = queue.poll();
                for (int neighbor : graph[node]) {
                    if (color[neighbor] == UNCOLORED) {
                        color[neighbor] = 1 - color[node];
                        queue.add(neighbor);
                    } else if (color[neighbor] == color[node]) {
                        return false;
                    }
                }
            }
        }
        return true;
    }
}
