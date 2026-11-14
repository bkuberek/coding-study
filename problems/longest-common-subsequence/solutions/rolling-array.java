import java.util.*;

public class Solution {
    public int longestCommonSubsequence(String text1, String text2) {
        // The answer is symmetric, so let the rows run along the shorter string.
        boolean firstIsLonger = text1.length() >= text2.length();
        String longer = firstIsLonger ? text1 : text2;
        String shorter = firstIsLonger ? text2 : text1;
        // previous[j] is the answer for the prefixes longer[:i - 1] and shorter[:j].
        int[] previous = new int[shorter.length() + 1];
        int[] current = new int[shorter.length() + 1];
        for (int i = 1; i <= longer.length(); i++) {
            for (int j = 1; j <= shorter.length(); j++) {
                if (longer.charAt(i - 1) == shorter.charAt(j - 1)) {
                    current[j] = previous[j - 1] + 1;
                } else {
                    current[j] = Math.max(previous[j], current[j - 1]);
                }
            }
            int[] swap = previous;
            previous = current;
            current = swap;
        }
        return previous[shorter.length()];
    }
}
