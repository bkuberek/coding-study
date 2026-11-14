import java.util.*;

public class Solution {
    public int numDecodings(String s) {
        // Before digit i: oneBack counts readings of s[0..i) and twoBack those of s[0..i - 1).
        int twoBack = 0;
        int oneBack = 1;
        for (int i = 0; i < s.length(); i++) {
            int current = s.charAt(i) != '0' ? oneBack : 0;
            if (i > 0) {
                int pair = (s.charAt(i - 1) - '0') * 10 + (s.charAt(i) - '0');
                if (pair >= 10 && pair <= 26) {
                    current += twoBack;
                }
            }
            twoBack = oneBack;
            oneBack = current;
        }
        return oneBack;
    }
}
