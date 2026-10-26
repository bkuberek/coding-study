public class Solution {
    private static final int LETTERS = 26;
    private static final int UNVISITED = 0;
    private static final int ON_PATH = 1;
    private static final int DONE = 2;

    public String alienOrder(String[] words) {
        boolean[] present = new boolean[LETTERS];
        for (String word : words) {
            for (char letter : word.toCharArray()) {
                present[letter - 'a'] = true;
            }
        }
        // before[x][y]: letter x must come before letter y.
        boolean[][] before = new boolean[LETTERS][LETTERS];
        for (int i = 0; i + 1 < words.length; i++) {
            String first = words[i];
            String second = words[i + 1];
            int shorter = Math.min(first.length(), second.length());
            int k = 0;
            while (k < shorter && first.charAt(k) == second.charAt(k)) {
                k++;
            }
            if (k < shorter) {
                before[first.charAt(k) - 'a'][second.charAt(k) - 'a'] = true;
            } else if (first.length() > second.length()) {
                return ""; // a word placed before its own proper prefix
            }
        }
        int[] state = new int[LETTERS];
        // Each letter lands in finished after every letter that must follow it.
        StringBuilder finished = new StringBuilder();
        for (int x = 0; x < LETTERS; x++) {
            if (present[x] && state[x] == UNVISITED && !visit(x, before, state, finished)) {
                return "";
            }
        }
        return finished.reverse().toString();
    }

    // Emit everything after x, then x; false if a rule loops back.
    private boolean visit(int x, boolean[][] before, int[] state, StringBuilder finished) {
        state[x] = ON_PATH;
        for (int y = 0; y < LETTERS; y++) {
            if (!before[x][y]) {
                continue;
            }
            if (state[y] == ON_PATH || (state[y] == UNVISITED && !visit(y, before, state, finished))) {
                return false;
            }
        }
        state[x] = DONE;
        finished.append((char) ('a' + x));
        return true;
    }
}
