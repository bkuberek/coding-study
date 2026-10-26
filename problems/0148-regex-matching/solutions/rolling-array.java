import java.util.*;

public class Solution {
    public boolean isMatch(String s, String p) {
        int columns = p.length();
        // previous[j]: s[:i - 1] matches p[:j]; current[j]: s[:i] matches p[:j].
        boolean[] previous = new boolean[columns + 1];
        boolean[] current = new boolean[columns + 1];
        for (int i = 0; i <= s.length(); i++) {
            current[0] = i == 0;
            for (int j = 1; j <= columns; j++) {
                if (p.charAt(j - 1) == '*') {
                    // "x*" matches nothing, or it matches s[i - 1] and possibly more before it.
                    boolean repeated = i > 0 && fits(s.charAt(i - 1), p.charAt(j - 2)) && previous[j];
                    current[j] = current[j - 2] || repeated;
                } else {
                    current[j] = i > 0 && fits(s.charAt(i - 1), p.charAt(j - 1)) && previous[j - 1];
                }
            }
            boolean[] swap = previous;
            previous = current;
            current = swap;
        }
        return previous[columns];
    }

    private static boolean fits(char letter, char item) {
        return item == '.' || item == letter;
    }
}
