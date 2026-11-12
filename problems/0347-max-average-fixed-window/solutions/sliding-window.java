public class Solution {
    public double maxWindowAverage(int[] nums, int k) {
        // A window sum is at most 10^5 * 10^4 = 10^9, which fits in an int.
        int windowSum = 0;
        for (int i = 0; i < k; i++) {
            windowSum += nums[i];
        }
        int best = windowSum;
        for (int right = k; right < nums.length; right++) {
            // Slide one step: the number at `right` enters and the one k places back leaves.
            windowSum += nums[right] - nums[right - k];
            best = Math.max(best, windowSum);
        }
        // Every window has k numbers, so the largest sum is the largest average. Divide once.
        return (double) best / k;
    }
}
