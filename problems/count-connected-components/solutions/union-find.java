public class Solution {
    private static final class DisjointSets {
        private final int[] parent;
        private final int[] size; // size[r]: number of nodes in the tree rooted at r

        DisjointSets(int count) {
            parent = new int[count];
            size = new int[count];
            for (int x = 0; x < count; x++) {
                parent[x] = x;
                size[x] = 1;
            }
        }

        int find(int x) {
            int root = x;
            while (parent[root] != root) {
                root = parent[root];
            }
            while (parent[x] != root) { // path compression: point the whole path at the root
                int next = parent[x];
                parent[x] = root;
                x = next;
            }
            return root;
        }

        // Merges the sets of a and b; false when they were already one set.
        boolean union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA == rootB) {
                return false;
            }
            if (size[rootA] < size[rootB]) {
                int held = rootA;
                rootA = rootB;
                rootB = held;
            }
            parent[rootB] = rootA; // union by size: the smaller tree goes under the larger
            size[rootA] += size[rootB];
            return true;
        }
    }

    public int countComponents(int n, int[][] edges) {
        DisjointSets sets = new DisjointSets(n);
        int components = n;
        for (int[] edge : edges) {
            if (sets.union(edge[0], edge[1])) {
                components--;
            }
        }
        return components;
    }
}
