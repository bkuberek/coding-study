import java.util.*;

public class Solution {
    public int numDecodings(String s) {
        // memo[start] is the number of readings of the suffix s[start..], or -1 when unknown.
        int[] memo = new int[s.length()];
        Arrays.fill(memo, -1);
        return waysFrom(0, s, memo);
    }

    private int waysFrom(int start, String s, int[] memo) {
        if (start == s.length()) {
            return 1;
        }
        if (s.charAt(start) == '0') {
            return 0;
        }
        if (memo[start] == -1) {
            int count = waysFrom(start + 1, s, memo);
            if (start + 1 < s.length()) {
                int pair = (s.charAt(start) - '0') * 10 + (s.charAt(start + 1) - '0');
                if (pair <= 26) {
                    count += waysFrom(start + 2, s, memo);
                }
            }
            memo[start] = count;
        }
        return memo[start];
    }
}
