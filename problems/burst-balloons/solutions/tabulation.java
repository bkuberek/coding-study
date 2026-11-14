import java.util.*;

public class Solution {
    public int maxCoins(int[] nums) {
        int size = nums.length + 2;
        int[] values = new int[size];
        values[0] = 1;
        values[size - 1] = 1;
        System.arraycopy(nums, 0, values, 1, nums.length);
        // best[left][right]: most coins from bursting everything strictly between left and right.
        int[][] best = new int[size][size];
        // An interval only depends on shorter ones, so fill by increasing gap right - left.
        for (int gap = 2; gap < size; gap++) {
            for (int left = 0; left + gap < size; left++) {
                int right = left + gap;
                int outer = values[left] * values[right];
                int most = 0;
                for (int last = left + 1; last < right; last++) {
                    most = Math.max(most, best[left][last] + outer * values[last] + best[last][right]);
                }
                best[left][right] = most;
            }
        }
        return best[0][size - 1];
    }
}
