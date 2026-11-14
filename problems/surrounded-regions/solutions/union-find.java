import java.util.*;

public class Solution {
    private static final class DisjointSet {
        private final int[] parent;
        private final byte[] rank;

        DisjointSet(int count) {
            parent = new int[count];
            rank = new byte[count];
            for (int i = 0; i < count; i++) {
                parent[i] = i;
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

        void union(int a, int b) {
            int rootA = find(a);
            int rootB = find(b);
            if (rootA == rootB) {
                return;
            }
            if (rank[rootA] < rank[rootB]) {
                int swap = rootA;
                rootA = rootB;
                rootB = swap;
            }
            parent[rootB] = rootA;
            if (rank[rootA] == rank[rootB]) {
                rank[rootA]++;
            }
        }
    }

    public void solve(char[][] board) {
        int rows = board.length;
        int cols = board[0].length;
        int edge = rows * cols; // a virtual node that every 'O' on the edge joins
        DisjointSet sets = new DisjointSet(rows * cols + 1);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (board[r][c] != 'O') {
                    continue;
                }
                int cell = r * cols + c;
                if (r == 0 || r == rows - 1 || c == 0 || c == cols - 1) {
                    sets.union(cell, edge);
                }
                if (c + 1 < cols && board[r][c + 1] == 'O') {
                    sets.union(cell, cell + 1);
                }
                if (r + 1 < rows && board[r + 1][c] == 'O') {
                    sets.union(cell, cell + cols);
                }
            }
        }
        int edgeRoot = sets.find(edge);
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                if (board[r][c] == 'O' && sets.find(r * cols + c) != edgeRoot) {
                    board[r][c] = 'X';
                }
            }
        }
    }
}
