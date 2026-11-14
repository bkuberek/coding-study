public class Solution {
    public int minSubArrayLen(int target, int[] nums) {
        int best = 0;
        for (int start = 0; start < nums.length; start++) {
            int total = 0;
            for (int end = start; end < nums.length; end++) {
                total += nums[end];
                if (total >= target) {
                    if (best == 0 || end - start + 1 < best) {
                        best = end - start + 1;
                    }
                    break;
                }
            }
        }
        return best;
    }
}
