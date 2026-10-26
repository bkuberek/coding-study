public class Solution {
    public boolean checkSubarraySum(int[] nums, int k) {
        for (int start = 0; start < nums.length; start++) {
            // Sums reach 10^14, so the running total must be a long.
            long total = nums[start];
            for (int end = start + 1; end < nums.length; end++) {
                total += nums[end];
                if (total % k == 0) {
                    return true;
                }
            }
        }
        return false;
    }
}
