import java.util.*;

public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    private int[][] matrix;
    // longest[r][c] caches the longest increasing path that starts at (r, c); 0 is unknown.
    private int[][] longest;

    public int longestIncreasingPath(int[][] matrix) {
        this.matrix = matrix;
        longest = new int[matrix.length][matrix[0].length];
        int answer = 0;
        for (int r = 0; r < matrix.length; r++) {
            for (int c = 0; c < matrix[0].length; c++) {
                answer = Math.max(answer, explore(r, c));
            }
        }
        return answer;
    }

    private int explore(int r, int c) {
        if (longest[r][c] == 0) {
            int best = 1;
            for (int[] step : STEPS) {
                int nr = r + step[0];
                int nc = c + step[1];
                if (nr >= 0 && nr < matrix.length && nc >= 0 && nc < matrix[0].length
                        && matrix[nr][nc] > matrix[r][c]) {
                    best = Math.max(best, 1 + explore(nr, nc));
                }
            }
            longest[r][c] = best;
        }
        return longest[r][c];
    }
}
