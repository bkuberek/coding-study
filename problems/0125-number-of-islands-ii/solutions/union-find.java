public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    private static final class DisjointSets {
        private final int[] parent;
        private final int[] size; // size[r]: number of cells in the tree rooted at r

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

    public int[] numIslands2(int m, int n, int[][] positions) {
        DisjointSets sets = new DisjointSets(m * n); // cell r * n + c
        boolean[] land = new boolean[m * n];
        int islands = 0;
        int[] counts = new int[positions.length];
        for (int i = 0; i < positions.length; i++) {
            int r = positions[i][0];
            int c = positions[i][1];
            int cell = r * n + c;
            if (!land[cell]) {
                land[cell] = true;
                islands++; // a new island, until it merges with its neighbors
                for (int[] step : STEPS) {
                    int nr = r + step[0];
                    int nc = c + step[1];
                    if (nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr * n + nc]
                            && sets.union(nr * n + nc, cell)) {
                        islands--;
                    }
                }
            }
            counts[i] = islands;
        }
        return counts;
    }
}
