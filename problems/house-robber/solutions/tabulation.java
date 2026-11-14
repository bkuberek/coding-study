import java.util.*;

public class Solution {
    public int rob(int[] nums) {
        // best[i] is the most cash obtainable from the first i houses.
        int[] best = new int[nums.length + 1];
        best[1] = nums[0];
        for (int i = 2; i <= nums.length; i++) {
            best[i] = Math.max(best[i - 1], best[i - 2] + nums[i - 1]);
        }
        return best[nums.length];
    }
}
