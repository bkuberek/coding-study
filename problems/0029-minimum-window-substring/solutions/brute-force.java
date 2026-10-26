public class Solution {
    public String minWindow(String s, String t) {
        int[] need = new int[128];
        for (int i = 0; i < t.length(); i++) {
            need[t.charAt(i)]++;
        }
        int bestStart = 0;
        int bestLength = 0;
        for (int start = 0; start < s.length(); start++) {
            int[] remaining = need.clone();
            int missing = t.length();
            for (int end = start; end < s.length(); end++) {
                if (remaining[s.charAt(end)]-- > 0) {
                    missing--;
                }
                if (missing == 0) {
                    if (bestLength == 0 || end - start + 1 < bestLength) {
                        bestStart = start;
                        bestLength = end - start + 1;
                    }
                    break;
                }
            }
        }
        return s.substring(bestStart, bestStart + bestLength);
    }
}
