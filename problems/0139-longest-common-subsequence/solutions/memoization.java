import java.util.*;

public class Solution {
    private String text1;
    private String text2;
    // best[i][j] caches the answer for the suffixes text1[i:] and text2[j:]; -1 is unknown.
    private int[][] best;

    public int longestCommonSubsequence(String text1, String text2) {
        this.text1 = text1;
        this.text2 = text2;
        best = new int[text1.length()][text2.length()];
        for (int[] row : best) {
            Arrays.fill(row, -1);
        }
        return solve(0, 0);
    }

    private int solve(int i, int j) {
        if (i == text1.length() || j == text2.length()) {
            return 0;
        }
        if (best[i][j] < 0) {
            best[i][j] = text1.charAt(i) == text2.charAt(j)
                    ? 1 + solve(i + 1, j + 1)
                    : Math.max(solve(i + 1, j), solve(i, j + 1));
        }
        return best[i][j];
    }
}
