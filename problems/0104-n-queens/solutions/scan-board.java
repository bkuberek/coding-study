import java.util.*;

public class Solution {
    public List<List<String>> solveNQueens(int n) {
        List<List<String>> boards = new ArrayList<>();
        place(n, 0, new int[n], boards);
        return boards;
    }

    // queenColumn[r] is the column of the queen in row r, for rows 0..row-1.
    private void place(int n, int row, int[] queenColumn, List<List<String>> boards) {
        if (row == n) {
            boards.add(drawBoard(queenColumn));
            return;
        }
        for (int col = 0; col < n; col++) {
            if (isSafe(queenColumn, row, col)) {
                queenColumn[row] = col;
                place(n, row + 1, queenColumn, boards);
            }
        }
    }

    private static boolean isSafe(int[] queenColumn, int row, int col) {
        for (int otherRow = 0; otherRow < row; otherRow++) {
            int otherCol = queenColumn[otherRow];
            if (col == otherCol || Math.abs(col - otherCol) == row - otherRow) {
                return false;
            }
        }
        return true;
    }

    private static List<String> drawBoard(int[] queenColumn) {
        int n = queenColumn.length;
        List<String> board = new ArrayList<>(n);
        for (int col : queenColumn) {
            board.add(".".repeat(col) + "Q" + ".".repeat(n - col - 1));
        }
        return board;
    }
}
