public class Solution {
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    public boolean exist(char[][] board, String word) {
        boolean[][] visited = new boolean[board.length][board[0].length];
        for (int r = 0; r < board.length; r++) {
            for (int c = 0; c < board[0].length; c++) {
                if (spellsFrom(board, word, visited, r, c, 0)) {
                    return true;
                }
            }
        }
        return false;
    }

    // Whether word[k..] can be spelled by a walk that starts at (r, c).
    private boolean spellsFrom(char[][] board, String word, boolean[][] visited, int r, int c, int k) {
        if (r < 0 || r >= board.length || c < 0 || c >= board[0].length
                || visited[r][c] || board[r][c] != word.charAt(k)) {
            return false;
        }
        if (k == word.length() - 1) {
            return true;
        }
        visited[r][c] = true;
        boolean found = false;
        for (int[] step : STEPS) {
            if (spellsFrom(board, word, visited, r + step[0], c + step[1], k + 1)) {
                found = true;
                break;
            }
        }
        visited[r][c] = false;
        return found;
    }
}
