import java.util.*;

public class Solution {
    private static final char USED = '#';
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public List<String> findWords(char[][] board, String[] words) {
        List<String> found = new ArrayList<>();
        for (String word : words) {
            if (onBoard(board, word)) {
                found.add(word);
            }
        }
        return found;
    }

    private static boolean onBoard(char[][] board, String word) {
        for (int row = 0; row < board.length; row++) {
            for (int col = 0; col < board[0].length; col++) {
                if (trace(board, word, row, col, 0)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** Can word[position..] be spelled starting at this cell? */
    private static boolean trace(char[][] board, String word, int row, int col, int position) {
        if (board[row][col] != word.charAt(position)) {
            return false;
        }
        if (position == word.length() - 1) {
            return true;
        }
        board[row][col] = USED;
        boolean found = false;
        for (int[] step : STEPS) {
            int r = row + step[0];
            int c = col + step[1];
            if (r >= 0 && r < board.length && c >= 0 && c < board[0].length && trace(board, word, r, c, position + 1)) {
                found = true;
                break;
            }
        }
        board[row][col] = word.charAt(position);
        return found;
    }
}
