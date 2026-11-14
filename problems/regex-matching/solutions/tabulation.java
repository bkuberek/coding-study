import java.util.*;

public class Solution {
    public boolean isMatch(String s, String p) {
        int rows = s.length();
        int columns = p.length();
        // matches[i][j]: s[:i] matches p[:j].
        boolean[][] matches = new boolean[rows + 1][columns + 1];
        matches[0][0] = true;
        for (int i = 0; i <= rows; i++) {
            for (int j = 1; j <= columns; j++) {
                if (p.charAt(j - 1) == '*') {
                    // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                    boolean repeated = i > 0 && fits(s.charAt(i - 1), p.charAt(j - 2)) && matches[i - 1][j];
                    matches[i][j] = matches[i][j - 2] || repeated;
                } else {
                    matches[i][j] = i > 0 && fits(s.charAt(i - 1), p.charAt(j - 1)) && matches[i - 1][j - 1];
                }
            }
        }
        return matches[rows][columns];
    }

    private static boolean fits(char letter, char item) {
        return item == '.' || item == letter;
    }
}
