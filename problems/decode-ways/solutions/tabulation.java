import java.util.*;

public class Solution {
    public int numDecodings(String s) {
        // ways[i] is the number of readings of the prefix s[0..i); the empty prefix has one.
        int n = s.length();
        int[] ways = new int[n + 1];
        ways[0] = 1;
        for (int i = 1; i <= n; i++) {
            if (s.charAt(i - 1) != '0') {
                ways[i] += ways[i - 1];
            }
            if (i >= 2) {
                int pair = (s.charAt(i - 2) - '0') * 10 + (s.charAt(i - 1) - '0');
                if (pair >= 10 && pair <= 26) {
                    ways[i] += ways[i - 2];
                }
            }
        }
        return ways[n];
    }
}
