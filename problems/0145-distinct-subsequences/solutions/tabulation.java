import java.util.*;

public class Solution {
    public int numDistinct(String s, String t) {
        int rows = s.length();
        int columns = t.length();
        // ways[i][j] counts the occurrences of t[:j] in s[:i]; the empty t[:0] occurs once.
        int[][] ways = new int[rows + 1][columns + 1];
        for (int i = 0; i <= rows; i++) {
            ways[i][0] = 1;
        }
        for (int i = 1; i <= rows; i++) {
            for (int j = 1; j <= columns; j++) {
                // Occurrences that skip s[i - 1], plus those that match it with t[j - 1].
                ways[i][j] = ways[i - 1][j];
                if (s.charAt(i - 1) == t.charAt(j - 1)) {
                    ways[i][j] += ways[i - 1][j - 1];
                }
            }
        }
        return ways[rows][columns];
    }
}
