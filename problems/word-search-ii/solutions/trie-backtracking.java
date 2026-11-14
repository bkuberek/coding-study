import java.util.*;

public class Solution {
    private static final char USED = '#';
    private static final int[][] STEPS = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};

    private static final class Node {
        final Node[] children = new Node[26];
        String word;
    }

    public List<String> findWords(char[][] board, String[] words) {
        Node root = new Node();
        for (String word : words) {
            Node node = root;
            for (int i = 0; i < word.length(); i++) {
                int index = word.charAt(i) - 'a';
                if (node.children[index] == null) {
                    node.children[index] = new Node();
                }
                node = node.children[index];
            }
            node.word = word;
        }
        List<String> found = new ArrayList<>();
        for (int row = 0; row < board.length; row++) {
            for (int col = 0; col < board[0].length; col++) {
                explore(board, row, col, root, found);
            }
        }
        return found;
    }

    private static void explore(char[][] board, int row, int col, Node parent, List<String> found) {
        char letter = board[row][col];
        if (letter == USED) {
            return;
        }
        Node node = parent.children[letter - 'a'];
        if (node == null) {
            return;
        }
        if (node.word != null) {
            found.add(node.word);
            node.word = null;
        }
        board[row][col] = USED;
        for (int[] step : STEPS) {
            int r = row + step[0];
            int c = col + step[1];
            if (r >= 0 && r < board.length && c >= 0 && c < board[0].length) {
                explore(board, r, c, node, found);
            }
        }
        board[row][col] = letter;
    }
}
