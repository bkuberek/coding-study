public class Solution {
    public int minSubArrayLen(int target, int[] nums) {
        int best = 0;
        int total = 0;
        int left = 0;
        for (int right = 0; right < nums.length; right++) {
            total += nums[right];
            while (total >= target) {
                if (best == 0 || right - left + 1 < best) {
                    best = right - left + 1;
                }
                total -= nums[left++];
            }
        }
        return best;
    }
}
