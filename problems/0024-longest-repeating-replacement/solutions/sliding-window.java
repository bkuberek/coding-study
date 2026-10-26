public class Solution {
    public int characterReplacement(String s, int k) {
        int[] counts = new int[26];
        int most = 0;
        int left = 0;
        int best = 0;
        for (int right = 0; right < s.length(); right++) {
            most = Math.max(most, ++counts[s.charAt(right) - 'A']);
            if (right - left + 1 - most > k) {
                counts[s.charAt(left) - 'A']--;
                left++;
            }
            best = Math.max(best, right - left + 1);
        }
        return best;
    }
}
