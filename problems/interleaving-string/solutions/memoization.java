import java.util.*;

public class Solution {
    private String s1;
    private String s2;
    private String s3;
    // known[i][j] caches whether s1[i:] and s2[j:] interleave to s3[i + j:]; null is unknown.
    private Boolean[][] known;

    public boolean isInterleave(String s1, String s2, String s3) {
        if (s1.length() + s2.length() != s3.length()) {
            return false;
        }
        this.s1 = s1;
        this.s2 = s2;
        this.s3 = s3;
        known = new Boolean[s1.length() + 1][s2.length() + 1];
        return solve(0, 0);
    }

    private boolean solve(int i, int j) {
        if (i == s1.length() && j == s2.length()) {
            return true;
        }
        if (known[i][j] == null) {
            char next = s3.charAt(i + j);
            // The next character of s3 comes from s1 or from s2.
            known[i][j] = (i < s1.length() && s1.charAt(i) == next && solve(i + 1, j))
                    || (j < s2.length() && s2.charAt(j) == next && solve(i, j + 1));
        }
        return known[i][j];
    }
}
