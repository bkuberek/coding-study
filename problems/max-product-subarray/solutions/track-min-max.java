import java.util.*;

public class Solution {
    public int maxProduct(int[] nums) {
        // largest and smallest are the extreme products of subarrays that end at the current index.
        int largest = nums[0];
        int smallest = nums[0];
        int best = nums[0];
        for (int i = 1; i < nums.length; i++) {
            int value = nums[i];
            int extendLargest = largest * value;
            int extendSmallest = smallest * value;
            largest = Math.max(value, Math.max(extendLargest, extendSmallest));
            smallest = Math.min(value, Math.min(extendLargest, extendSmallest));
            best = Math.max(best, largest);
        }
        return best;
    }
}
