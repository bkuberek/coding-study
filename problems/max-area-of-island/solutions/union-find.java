import java.util.*;

public class Solution {
    private static final class DisjointSet {
        private final int[] parent;
        private final int[] size;

        DisjointSet(int count) {
            parent = new int[count];
            size = new int[count];
            for (int i = 0; i < count; i++) {
                parent[i] = i;
                size[i] = 1;
            }
        }

        int find(int cell) {
            int root = cell;
            while (parent[root] != root) {
                root = parent[root];
            }
            while (parent[cell] != root) {
                int next = parent[cell];
                parent[cell] = root;
                cell = next;
            }
            return root;
        }

        /** Merges the groups of a and b and returns the size of the merged group. */
        int union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA != rootB) {
                if (size[rootA] < size[rootB]) {
                    int swap = rootA;
                    rootA = rootB;
                    rootB = swap;
                }
                parent[rootB] = rootA;
                size[rootA] += size[rootB];
            }
            return size[rootA];
        }
    }

    public int maxAreaOfIsland(int[][] grid) {
        int rows = grid.length;
        int cols = grid[0].length;
        DisjointSet sets = new DisjointSet(rows * cols);
        int best = 0;
        for (int row = 0; row < rows; row++) {
            for (int col = 0; col < cols; col++) {
                if (grid[row][col] != 1) {
                    continue;
                }
                int cell = row * cols + col;
                best = Math.max(best, 1);
                if (col + 1 < cols && grid[row][col + 1] == 1) {
                    best = Math.max(best, sets.union(cell, cell + 1));
                }
                if (row + 1 < rows && grid[row + 1][col] == 1) {
                    best = Math.max(best, sets.union(cell, cell + cols));
                }
            }
        }
        return best;
    }
}
