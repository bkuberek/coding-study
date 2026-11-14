import java.util.*;

public class Solution {
    public int longestCommonSubsequence(String text1, String text2) {
        int rows = text1.length();
        int columns = text2.length();
        // best[i][j] is the answer for the prefixes text1[:i] and text2[:j]; row and column 0
        // stand for an empty prefix.
        int[][] best = new int[rows + 1][columns + 1];
        for (int i = 1; i <= rows; i++) {
            for (int j = 1; j <= columns; j++) {
                if (text1.charAt(i - 1) == text2.charAt(j - 1)) {
                    best[i][j] = best[i - 1][j - 1] + 1;
                } else {
                    best[i][j] = Math.max(best[i - 1][j], best[i][j - 1]);
                }
            }
        }
        return best[rows][columns];
    }
}
