import java.util.*;

public class Solution {
    public boolean checkValidString(String s) {
        int n = s.length();
        // possible[k] is true when some choice of wildcards gives the prefix an open count of k.
        boolean[] possible = new boolean[n + 2];
        boolean[] following = new boolean[n + 2];
        possible[0] = true;
        for (int i = 0; i < n; i++) {
            char c = s.charAt(i);
            Arrays.fill(following, false);
            boolean any = false;
            for (int open = 0; open <= n; open++) {
                if (!possible[open]) {
                    continue;
                }
                if (c != ')') {
                    following[open + 1] = true; // "(" or a wildcard as "("
                }
                if (c != '(' && open > 0) {
                    following[open - 1] = true; // ")" or a wildcard as ")"
                }
                if (c == '*') {
                    following[open] = true; // a wildcard as nothing
                }
                any = true;
            }
            if (!any) {
                return false;
            }
            boolean[] swap = possible;
            possible = following;
            following = swap;
        }
        return possible[0];
    }
}
