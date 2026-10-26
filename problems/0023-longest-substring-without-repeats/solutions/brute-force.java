public class Solution {
    public int lengthOfLongestSubstring(String s) {
        int best = 0;
        for (int start = 0; start < s.length(); start++) {
            boolean[] seen = new boolean[128];
            int end = start;
            while (end < s.length() && !seen[s.charAt(end)]) {
                seen[s.charAt(end)] = true;
                end++;
            }
            best = Math.max(best, end - start);
        }
        return best;
    }
}
