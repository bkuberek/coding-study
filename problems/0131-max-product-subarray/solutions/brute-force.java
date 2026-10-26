import java.util.*;

public class Solution {
    public int maxProduct(int[] nums) {
        int best = nums[0];
        for (int start = 0; start < nums.length; start++) {
            int product = 1;
            for (int end = start; end < nums.length; end++) {
                product *= nums[end];
                best = Math.max(best, product);
            }
        }
        return best;
    }
}
