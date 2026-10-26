import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public int[] numIslands2(int m, int n, int[][] positions) {
        boolean[] land = new boolean[m * n]; // cell r * n + c
        List<Integer> cells = new ArrayList<>(); // every land cell, each once
        // seenInRound[cell] == round marks a cell visited by the current recount, so the
        // array is allocated once instead of once per operation.
        int[] seenInRound = new int[m * n];
        int[] counts = new int[positions.length];
        for (int i = 0; i < positions.length; i++) {
            int cell = positions[i][0] * n + positions[i][1];
            if (!land[cell]) {
                land[cell] = true;
                cells.add(cell);
            }
            counts[i] = countIslands(m, n, land, cells, seenInRound, i + 1);
        }
        return counts;
    }

    private static int countIslands(int m, int n, boolean[] land, List<Integer> cells, int[] seenInRound,
                                    int round) {
        ArrayDeque<Integer> stack = new ArrayDeque<>();
        int islands = 0;
        for (int start : cells) {
            if (seenInRound[start] == round) {
                continue;
            }
            islands++;
            seenInRound[start] = round;
            stack.push(start);
            while (!stack.isEmpty()) {
                int cell = stack.pop();
                int r = cell / n;
                int c = cell % n;
                for (int[] step : STEPS) {
                    int nr = r + step[0];
                    int nc = c + step[1];
                    int neighbor = nr * n + nc;
                    if (nr >= 0 && nr < m && nc >= 0 && nc < n && land[neighbor] && seenInRound[neighbor] != round) {
                        seenInRound[neighbor] = round;
                        stack.push(neighbor);
                    }
                }
            }
        }
        return islands;
    }
}
