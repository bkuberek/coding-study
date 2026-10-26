public class Solution {
    public int countComponents(int n, int[][] edges) {
        int[] parent = new int[n]; // parent[x] == x marks a root
        for (int x = 0; x < n; x++) {
            parent[x] = x;
        }
        int components = n;
        for (int[] edge : edges) {
            int rootA = find(parent, edge[0]);
            int rootB = find(parent, edge[1]);
            if (rootA != rootB) {
                parent[rootA] = rootB; // no balancing: trees can grow into long chains
                components--;
            }
        }
        return components;
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            x = parent[x];
        }
        return x;
    }
}
