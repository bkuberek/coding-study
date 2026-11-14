public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[] numIslands2(int m, int n, int[][] positions) {
        int[] parent = new int[m * n]; // cell r * n + c; parent[x] == x marks a root
        for (int x = 0; x < parent.length; x++) {
            parent[x] = x;
        }
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
                    if (nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr * n + nc]) {
                        int rootNeighbor = find(parent, nr * n + nc);
                        int rootCell = find(parent, cell);
                        if (rootNeighbor != rootCell) {
                            parent[rootNeighbor] = rootCell; // no balancing: chains can grow
                            islands--;
                        }
                    }
                }
            }
            counts[i] = islands;
        }
        return counts;
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            x = parent[x];
        }
        return x;
    }
}
