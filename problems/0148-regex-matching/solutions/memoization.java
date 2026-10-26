import java.util.*;

public class Solution {
    private String s;
    private String p;
    // known[i][j] caches whether s[i:] matches p[j:]; null is unknown.
    private Boolean[][] known;

    public boolean isMatch(String s, String p) {
        this.s = s;
        this.p = p;
        known = new Boolean[s.length() + 1][p.length() + 1];
        return solve(0, 0);
    }

    private boolean solve(int i, int j) {
        if (j == p.length()) {
            return i == s.length();
        }
        if (known[i][j] == null) {
            boolean first = i < s.length() && (p.charAt(j) == s.charAt(i) || p.charAt(j) == '.');
            if (j + 1 < p.length() && p.charAt(j + 1) == '*') {
                // Skip "x*" entirely, or let it eat one more character and stay on it.
                known[i][j] = solve(i, j + 2) || (first && solve(i + 1, j));
            } else {
                known[i][j] = first && solve(i + 1, j + 1);
            }
        }
        return known[i][j];
    }
}
