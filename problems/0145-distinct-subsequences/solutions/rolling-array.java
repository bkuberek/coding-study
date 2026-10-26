import java.util.*;

public class Solution {
    public int numDistinct(String s, String t) {
        // ways[j] counts the occurrences of t[:j] in the prefix of s read so far.
        int[] ways = new int[t.length() + 1];
        ways[0] = 1;
        for (int i = 0; i < s.length(); i++) {
            char character = s.charAt(i);
            // Right to left: ways[j - 1] still excludes this character, so it is used once.
            for (int j = t.length(); j > 0; j--) {
                if (t.charAt(j - 1) == character) {
                    ways[j] += ways[j - 1];
                }
            }
        }
        return ways[t.length()];
    }
}
