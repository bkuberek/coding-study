import java.util.*;

public class Solution {
    public String minWindow(String s, String t) {
        int[] deficit = new int[128];
        for (int i = 0; i < t.length(); i++) {
            deficit[t.charAt(i)]++;
        }
        List<Integer> useful = new ArrayList<>();
        for (int i = 0; i < s.length(); i++) {
            if (deficit[s.charAt(i)] > 0) {
                useful.add(i);
            }
        }
        int missing = t.length();
        int bestStart = 0;
        int bestLength = 0;
        int left = 0;
        for (int right : useful) {
            if (deficit[s.charAt(right)]-- > 0) {
                missing--;
            }
            while (missing == 0) {
                int start = useful.get(left);
                if (bestLength == 0 || right - start + 1 < bestLength) {
                    bestStart = start;
                    bestLength = right - start + 1;
                }
                if (++deficit[s.charAt(start)] > 0) {
                    missing++;
                }
                left++;
            }
        }
        return s.substring(bestStart, bestStart + bestLength);
    }
}
