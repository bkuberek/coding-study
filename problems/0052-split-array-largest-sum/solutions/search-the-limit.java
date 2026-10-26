public class Solution {
    public int splitArray(int[] nums, int k) {
        // Feasibility only improves as the limit grows: find the smallest feasible limit.
        int low = 0;
        int high = 0;
        for (int value : nums) {
            low = Math.max(low, value);
            high += value;
        }
        while (low < high) {
            int limit = low + (high - low) / 2;
            if (piecesNeeded(nums, limit) <= k) {
                high = limit;
            } else {
                low = limit + 1;
            }
        }
        return low;
    }

    // Greedy: extend the current piece while it fits under the limit.
    private static int piecesNeeded(int[] nums, int limit) {
        int pieces = 1;
        int running = 0;
        for (int value : nums) {
            if (running + value > limit) {
                pieces++;
                running = value;
            } else {
                running += value;
            }
        }
        return pieces;
    }
}
