public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    private static final char USED = '#';

    public boolean exist(char[][] board, String word) {
        int[] available = new int[128];
        for (char[] row : board) {
            for (char letter : row) {
                available[letter]++;
            }
        }
        int[] needed = new int[128];
        for (char letter : word.toCharArray()) {
            if (++needed[letter] > available[letter]) {
                return false;
            }
        }
        // A walk read backwards is also a walk: start from whichever end is rarer on the board.
        char[] target = word.toCharArray();
        if (available[target[0]] > available[target[target.length - 1]]) {
            target = new StringBuilder(word).reverse().toString().toCharArray();
        }
        for (int r = 0; r < board.length; r++) {
            for (int c = 0; c < board[0].length; c++) {
                if (spellsFrom(board, target, r, c, 0)) {
                    return true;
                }
            }
        }
        return false;
    }

    private boolean spellsFrom(char[][] board, char[] target, int r, int c, int k) {
        if (board[r][c] != target[k]) {
            return false;
        }
        if (k == target.length - 1) {
            return true;
        }
        board[r][c] = USED;
        boolean found = false;
        for (int[] step : STEPS) {
            int nr = r + step[0];
            int nc = c + step[1];
            if (nr >= 0 && nr < board.length && nc >= 0 && nc < board[0].length
                    && spellsFrom(board, target, nr, nc, k + 1)) {
                found = true;
                break;
            }
        }
        board[r][c] = target[k];
        return found;
    }
}
