public class Solution {
    public int[] searchRange(int[] nums, int target) {
        int first = firstIndex(nums, target, false);
        if (first == nums.length || nums[first] != target) {
            return new int[] {-1, -1};
        }
        return new int[] {first, firstIndex(nums, target, true) - 1};
    }

    // The smallest index whose value is >= target (or > target when strict), or nums.length.
    private static int firstIndex(int[] nums, int target, boolean strict) {
        int low = 0;
        int high = nums.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            boolean past = strict ? nums[middle] > target : nums[middle] >= target;
            if (past) {
                high = middle;
            } else {
                low = middle + 1;
            }
        }
        return low;
    }
}
