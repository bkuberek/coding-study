public class Solution {
    public int splitArray(int[] nums, int k) {
        int n = nums.length;
        int[] prefix = new int[n + 1];
        for (int i = 0; i < n; i++) {
            prefix[i + 1] = prefix[i] + nums[i];
        }
        // best[i]: the smallest cost of cutting the first i values into the current number of pieces.
        int[] best = prefix.clone();
        for (int pieces = 2; pieces <= k; pieces++) {
            int[] next = new int[n + 1];
            for (int end = pieces; end <= n; end++) {
                int cost = Integer.MAX_VALUE;
                for (int cut = pieces - 1; cut < end; cut++) {
                    cost = Math.min(cost, Math.max(best[cut], prefix[end] - prefix[cut]));
                }
                next[end] = cost;
            }
            best = next;
        }
        return best[n];
    }
}
