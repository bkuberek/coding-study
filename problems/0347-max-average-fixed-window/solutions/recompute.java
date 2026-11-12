public class Solution {
    public double maxWindowAverage(int[] nums, int k) {
        double best = Double.NEGATIVE_INFINITY;
        for (int start = 0; start + k <= nums.length; start++) {
            int sum = 0;
            for (int i = start; i < start + k; i++) {
                sum += nums[i];
            }
            best = Math.max(best, (double) sum / k);
        }
        return best;
    }
}
