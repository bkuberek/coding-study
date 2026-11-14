import java.util.*;

public class Solution {
    private int[] values;
    // best[left][right] caches the most coins from bursting every balloon strictly between
    // left and right, while those two are still standing; -1 is unknown.
    private int[][] best;

    public int maxCoins(int[] nums) {
        // Pad with the virtual balloons of value 1 at both ends.
        values = new int[nums.length + 2];
        values[0] = 1;
        values[nums.length + 1] = 1;
        System.arraycopy(nums, 0, values, 1, nums.length);
        best = new int[values.length][values.length];
        for (int[] row : best) {
            Arrays.fill(row, -1);
        }
        return solve(0, values.length - 1);
    }

    private int solve(int left, int right) {
        if (right - left < 2) {
            return 0;
        }
        if (best[left][right] < 0) {
            int most = 0;
            // The balloon burst last between them has exactly left and right as neighbors.
            for (int last = left + 1; last < right; last++) {
                int coins = solve(left, last) + values[left] * values[last] * values[right] + solve(last, right);
                most = Math.max(most, coins);
            }
            best[left][right] = most;
        }
        return best[left][right];
    }
}
