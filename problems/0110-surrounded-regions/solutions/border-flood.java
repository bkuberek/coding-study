import java.util.*;

public class Solution {
    private static final char SAFE = 'S';
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public void solve(char[][] board) {
        int rows = board.length;
        int cols = board[0].length;
        // Every 'O' on the edge is safe; so is everything connected to one of them.
        Deque<int[]> stack = new ArrayDeque<>();
        for (int r = 0; r < rows; r++) {
            for (int c = 0; c < cols; c++) {
                boolean onEdge = r == 0 || r == rows - 1 || c == 0 || c == cols - 1;
                if (onEdge && board[r][c] == 'O') {
                    board[r][c] = SAFE;
                    stack.push(new int[] {r, c});
                }
            }
        }
        while (!stack.isEmpty()) {
            int[] cell = stack.pop();
            for (int[] step : STEPS) {
                int r = cell[0] + step[0];
                int c = cell[1] + step[1];
                if (r >= 0 && r < rows && c >= 0 && c < cols && board[r][c] == 'O') {
                    board[r][c] = SAFE;
                    stack.push(new int[] {r, c});
                }
            }
        }
        for (char[] row : board) {
            for (int c = 0; c < cols; c++) {
                row[c] = row[c] == SAFE ? 'O' : 'X';
            }
        }
    }
}
