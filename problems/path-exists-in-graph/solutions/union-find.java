public class Solution {
    private static final class DisjointSet {
        private final int[] parent;
        private final int[] size;

        DisjointSet(int count) {
            parent = new int[count];
            size = new int[count];
            for (int node = 0; node < count; node++) {
                parent[node] = node;
                size[node] = 1;
            }
        }

        int find(int node) {
            // Path halving: point every other node on the way up at its grandparent.
            while (parent[node] != node) {
                parent[node] = parent[parent[node]];
                node = parent[node];
            }
            return node;
        }

        void union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA == rootB) {
                return;
            }
            if (size[rootA] < size[rootB]) {
                int swap = rootA;
                rootA = rootB;
                rootB = swap;
            }
            parent[rootB] = rootA;
            size[rootA] += size[rootB];
        }
    }

    public boolean hasPath(int n, int[][] edges, int source, int target) {
        DisjointSet sets = new DisjointSet(n);
        for (int[] edge : edges) {
            sets.union(edge[0], edge[1]);
        }
        return sets.find(source) == sets.find(target);
    }
}
