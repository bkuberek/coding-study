public class Solution {
    public int characterReplacement(String s, int k) {
        int best = 0;
        for (int start = 0; start < s.length(); start++) {
            int[] counts = new int[26];
            int most = 0;
            for (int end = start; end < s.length(); end++) {
                most = Math.max(most, ++counts[s.charAt(end) - 'A']);
                if (end - start + 1 - most > k) {
                    break;
                }
                best = Math.max(best, end - start + 1);
            }
        }
        return best;
    }
}
