import java.util.*;

public class Solution {
    public List<List<String>> solveNQueens(int n) {
        List<List<String>> boards = new ArrayList<>();
        place(n, 0, 0, 0, 0, new int[n], boards);
        return boards;
    }

    // Each mask marks the squares of the current row attacked along one kind of line.
    private void place(int n, int row, int columns, int diagonals, int antiDiagonals, int[] queenColumn,
                       List<List<String>> boards) {
        int full = (1 << n) - 1;
        if (columns == full) {
            boards.add(drawBoard(queenColumn));
            return;
        }
        int free = full & ~(columns | diagonals | antiDiagonals);
        while (free != 0) {
            int bit = free & -free; // lowest free square
            free ^= bit;
            queenColumn[row] = Integer.numberOfTrailingZeros(bit);
            // Moving one row down shifts each diagonal attack one column over.
            place(n, row + 1, columns | bit, ((diagonals | bit) << 1) & full, (antiDiagonals | bit) >> 1,
                    queenColumn, boards);
        }
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
