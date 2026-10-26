import java.util.*;

public class Solution {
    private static final int SIDE = 9;
    private static final int BOX = 3;
    private static final char EMPTY = '.';

    public boolean isValidSudoku(char[][] board) {
        List<Set<Character>> rows = new ArrayList<>();
        List<Set<Character>> columns = new ArrayList<>();
        List<Set<Character>> boxes = new ArrayList<>();
        for (int i = 0; i < SIDE; i++) {
            rows.add(new HashSet<>());
            columns.add(new HashSet<>());
            boxes.add(new HashSet<>());
        }
        for (int row = 0; row < SIDE; row++) {
            for (int column = 0; column < SIDE; column++) {
                char digit = board[row][column];
                if (digit == EMPTY) {
                    continue;
                }
                int box = (row / BOX) * BOX + column / BOX;
                // add returns false when the digit is already present.
                if (!rows.get(row).add(digit)
                        || !columns.get(column).add(digit)
                        || !boxes.get(box).add(digit)) {
                    return false;
                }
            }
        }
        return true;
    }
}
