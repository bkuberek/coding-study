public class Solution {
    public int characterReplacement(String s, int k) {
        int best = 0;
        for (char target = 'A'; target <= 'Z'; target++) {
            if (s.indexOf(target) < 0) {
                continue;
            }
            int left = 0;
            int others = 0;
            for (int right = 0; right < s.length(); right++) {
                if (s.charAt(right) != target) {
                    others++;
                }
                while (others > k) {
                    if (s.charAt(left) != target) {
                        others--;
                    }
                    left++;
                }
                best = Math.max(best, right - left + 1);
            }
        }
        return best;
    }
}
