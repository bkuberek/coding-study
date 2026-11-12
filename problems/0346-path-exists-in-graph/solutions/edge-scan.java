public class Solution {
    public boolean hasPath(int n, int[][] edges, int source, int target) {
        boolean[] reached = new boolean[n];
        reached[source] = true;
        boolean changed = true;
        while (changed && !reached[target]) {
            changed = false;
            for (int[] edge : edges) {
                // A connection with exactly one reached end brings the other end in.
                if (reached[edge[0]] != reached[edge[1]]) {
                    reached[edge[0]] = true;
                    reached[edge[1]] = true;
                    changed = true;
                }
            }
        }
        return reached[target];
    }
}
