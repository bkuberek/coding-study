import java.util.*;

public class Solution {
    private static final int SIDE = 9;
    private static final int BOX = 3;
    private static final char EMPTY = '.';

    public boolean isValidSudoku(char[][] board) {
        // Bit d - 1 of a mask is set once digit d has been seen in that row, column or box.
        int[] rows = new int[SIDE];
        int[] columns = new int[SIDE];
        int[] boxes = new int[SIDE];
        for (int row = 0; row < SIDE; row++) {
            for (int column = 0; column < SIDE; column++) {
                char cell = board[row][column];
                if (cell == EMPTY) {
                    continue;
                }
                int bit = 1 << (cell - '1');
                int box = (row / BOX) * BOX + column / BOX;
                if (((rows[row] | columns[column] | boxes[box]) & bit) != 0) {
                    return false;
                }
                rows[row] |= bit;
                columns[column] |= bit;
                boxes[box] |= bit;
            }
        }
        return true;
    }
}
