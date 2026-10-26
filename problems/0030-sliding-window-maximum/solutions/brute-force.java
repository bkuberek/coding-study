public class Solution {
    public int[] maxSlidingWindow(int[] nums, int k) {
        int[] maxima = new int[nums.length - k + 1];
        for (int start = 0; start < maxima.length; start++) {
            int best = nums[start];
            for (int i = start + 1; i < start + k; i++) {
                best = Math.max(best, nums[i]);
            }
            maxima[start] = best;
        }
        return maxima;
    }
}
