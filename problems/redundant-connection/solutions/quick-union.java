public class Solution {
    public int[] findRedundantConnection(int[][] edges) {
        int[] parent = new int[edges.length + 1]; // parent[x] == x marks a root
        for (int x = 0; x < parent.length; x++) {
            parent[x] = x;
        }
        for (int[] edge : edges) {
            int rootA = find(parent, edge[0]);
            int rootB = find(parent, edge[1]);
            if (rootA == rootB) {
                return edge; // the ends are already connected: this edge closes the cycle
            }
            parent[rootA] = rootB; // no balancing: trees can grow into long chains
        }
        return new int[0];
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            x = parent[x];
        }
        return x;
    }
}
