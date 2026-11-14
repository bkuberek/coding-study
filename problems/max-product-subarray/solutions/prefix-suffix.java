import java.util.*;

public class Solution {
    public int maxProduct(int[] nums) {
        // Within a zero-free run, the best product is a prefix or a suffix of the run, so the
        // running products from both ends (restarted after each zero) cover every candidate.
        int best = Arrays.stream(nums).max().getAsInt();
        int fromLeft = 1;
        int fromRight = 1;
        int n = nums.length;
        for (int i = 0; i < n; i++) {
            fromLeft = (fromLeft == 0 ? 1 : fromLeft) * nums[i];
            fromRight = (fromRight == 0 ? 1 : fromRight) * nums[n - 1 - i];
            best = Math.max(best, Math.max(fromLeft, fromRight));
        }
        return best;
    }
}
