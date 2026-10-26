import java.util.*;

public class Solution {
    public int maxSubArray(int[] nums) {
        // endingHere is the best sum of a subarray that ends at the current index.
        int endingHere = nums[0];
        int best = nums[0];
        for (int index = 1; index < nums.length; index++) {
            endingHere = Math.max(nums[index], endingHere + nums[index]);
            best = Math.max(best, endingHere);
        }
        return best;
    }
}
