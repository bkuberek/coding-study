public class Solution {
    public String minWindow(String s, String t) {
        int[] deficit = new int[128];
        for (int i = 0; i < t.length(); i++) {
            deficit[t.charAt(i)]++;
        }
        int missing = t.length();
        int bestStart = 0;
        int bestLength = 0;
        int left = 0;
        for (int right = 0; right < s.length(); right++) {
            if (deficit[s.charAt(right)]-- > 0) {
                missing--;
            }
            while (missing == 0) {
                if (bestLength == 0 || right - left + 1 < bestLength) {
                    bestStart = left;
                    bestLength = right - left + 1;
                }
                if (++deficit[s.charAt(left)] > 0) {
                    missing++;
                }
                left++;
            }
        }
        return s.substring(bestStart, bestStart + bestLength);
    }
}
