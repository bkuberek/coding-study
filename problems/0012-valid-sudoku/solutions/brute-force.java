import java.util.*;

public class Solution {
    private static final int SIDE = 9;
    private static final int BOX = 3;
    private static final char EMPTY = '.';

    public boolean isValidSudoku(char[][] board) {
        for (int row = 0; row < SIDE; row++) {
            for (int column = 0; column < SIDE; column++) {
                char digit = board[row][column];
                if (digit != EMPTY && repeats(board, row, column, digit)) {
                    return false;
                }
            }
        }
        return true;
    }

    // Whether another cell in the same row, column or box holds `digit`.
    private static boolean repeats(char[][] board, int row, int column, char digit) {
        int top = row - row % BOX;
        int left = column - column % BOX;
        for (int i = 0; i < SIDE; i++) {
            if (i != column && board[row][i] == digit) {
                return true;
            }
            if (i != row && board[i][column] == digit) {
                return true;
            }
            int boxRow = top + i / BOX;
            int boxColumn = left + i % BOX;
            if ((boxRow != row || boxColumn != column) && board[boxRow][boxColumn] == digit) {
                return true;
            }
        }
        return false;
    }
}
