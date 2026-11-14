import java.util.*;

public class Solution {
    public boolean isInterleave(String s1, String s2, String s3) {
        int rows = s1.length();
        int columns = s2.length();
        if (rows + columns != s3.length()) {
            return false;
        }
        // reach[i][j]: s1[:i] and s2[:j] interleave to s3[:i + j].
        boolean[][] reach = new boolean[rows + 1][columns + 1];
        reach[0][0] = true;
        for (int i = 0; i <= rows; i++) {
            for (int j = 0; j <= columns; j++) {
                // The last character of s3[:i + j] came from s1 or from s2.
                if (i > 0 && reach[i - 1][j] && s1.charAt(i - 1) == s3.charAt(i + j - 1)) {
                    reach[i][j] = true;
                } else if (j > 0 && reach[i][j - 1] && s2.charAt(j - 1) == s3.charAt(i + j - 1)) {
                    reach[i][j] = true;
                }
            }
        }
        return reach[rows][columns];
    }
}
