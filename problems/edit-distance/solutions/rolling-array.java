import java.util.*;

public class Solution {
    public int minDistance(String word1, String word2) {
        // The distance is symmetric (insertions and deletions swap roles), so let the rows run
        // along the shorter word.
        boolean firstIsLonger = word1.length() >= word2.length();
        String longer = firstIsLonger ? word1 : word2;
        String shorter = firstIsLonger ? word2 : word1;
        // previous[j] is the distance between longer[:i - 1] and shorter[:j].
        int[] previous = new int[shorter.length() + 1];
        int[] current = new int[shorter.length() + 1];
        for (int j = 0; j <= shorter.length(); j++) {
            previous[j] = j;
        }
        for (int i = 1; i <= longer.length(); i++) {
            current[0] = i;
            for (int j = 1; j <= shorter.length(); j++) {
                if (longer.charAt(i - 1) == shorter.charAt(j - 1)) {
                    current[j] = previous[j - 1];
                } else {
                    current[j] = 1 + Math.min(previous[j], Math.min(current[j - 1], previous[j - 1]));
                }
            }
            int[] swap = previous;
            previous = current;
            current = swap;
        }
        return previous[shorter.length()];
    }
}
