import java.util.*;

public class Solution {
    private String s;
    private String t;
    // ways[i][j] caches the occurrences of t[j:] as a subsequence of s[i:]; -1 is unknown.
    private int[][] ways;

    public int numDistinct(String s, String t) {
        this.s = s;
        this.t = t;
        ways = new int[s.length()][t.length()];
        for (int[] row : ways) {
            Arrays.fill(row, -1);
        }
        return count(0, 0);
    }

    private int count(int i, int j) {
        if (j == t.length()) {
            return 1; // the empty suffix of t occurs once
        }
        if (s.length() - i < t.length() - j) {
            return 0; // not enough characters left in s
        }
        if (ways[i][j] < 0) {
            // Either s[i] is skipped, or it is matched with t[j].
            ways[i][j] = count(i + 1, j) + (s.charAt(i) == t.charAt(j) ? count(i + 1, j + 1) : 0);
        }
        return ways[i][j];
    }
}
