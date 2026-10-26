import java.util.*;

public class Solution {
    private int n;
    private int[] queenColumn;
    private boolean[] columns;
    // Squares on one diagonal share row - col (shifted by n - 1 to index from 0); on one
    // anti-diagonal they share row + col.
    private boolean[] diagonals;
    private boolean[] antiDiagonals;
    private List<List<String>> boards;

    public List<List<String>> solveNQueens(int n) {
        this.n = n;
        queenColumn = new int[n];
        columns = new boolean[n];
        diagonals = new boolean[2 * n - 1];
        antiDiagonals = new boolean[2 * n - 1];
        boards = new ArrayList<>();
        place(0);
        return boards;
    }

    private void place(int row) {
        if (row == n) {
            boards.add(drawBoard());
            return;
        }
        for (int col = 0; col < n; col++) {
            int diagonal = row - col + n - 1;
            int antiDiagonal = row + col;
            if (columns[col] || diagonals[diagonal] || antiDiagonals[antiDiagonal]) {
                continue;
            }
            columns[col] = diagonals[diagonal] = antiDiagonals[antiDiagonal] = true;
            queenColumn[row] = col;
            place(row + 1);
            columns[col] = diagonals[diagonal] = antiDiagonals[antiDiagonal] = false;
        }
    }

    private List<String> drawBoard() {
        List<String> board = new ArrayList<>(n);
        for (int col : queenColumn) {
            board.add(".".repeat(col) + "Q" + ".".repeat(n - col - 1));
        }
        return board;
    }
}
