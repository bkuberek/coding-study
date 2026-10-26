import java.util.*;

public class Solution {
    public int maxSubArray(int[] nums) {
        return bestIn(nums, 0, nums.length - 1);
    }

    /** The best subarray sum within nums[low..high] (inclusive). */
    private int bestIn(int[] nums, int low, int high) {
        if (low == high) {
            return nums[low];
        }
        int middle = (low + high) >>> 1;
        // The best crossing subarray is a best suffix of the left half plus a best prefix of
        // the right half.
        int leftSuffix = nums[middle];
        int total = 0;
        for (int i = middle; i >= low; i--) {
            total += nums[i];
            leftSuffix = Math.max(leftSuffix, total);
        }
        int rightPrefix = nums[middle + 1];
        total = 0;
        for (int i = middle + 1; i <= high; i++) {
            total += nums[i];
            rightPrefix = Math.max(rightPrefix, total);
        }
        int halves = Math.max(bestIn(nums, low, middle), bestIn(nums, middle + 1, high));
        return Math.max(halves, leftSuffix + rightPrefix);
    }
}
