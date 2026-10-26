public class Solution {
    public int longestOnes(int[] nums, int k) {
        int best = 0;
        for (int start = 0; start < nums.length; start++) {
            int zeros = 0;
            int end = start;
            while (end < nums.length) {
                if (nums[end] == 0) {
                    if (zeros == k) {
                        break;
                    }
                    zeros++;
                }
                end++;
            }
            best = Math.max(best, end - start);
        }
        return best;
    }
}
