public class Solution {
    public int[] searchRange(int[] nums, int target) {
        int low = 0;
        int high = nums.length - 1;
        while (low <= high) {
            int middle = (low + high) >>> 1;
            if (nums[middle] == target) {
                int first = middle;
                int last = middle;
                while (first > 0 && nums[first - 1] == target) {
                    first--;
                }
                while (last < nums.length - 1 && nums[last + 1] == target) {
                    last++;
                }
                return new int[] {first, last};
            }
            if (nums[middle] < target) {
                low = middle + 1;
            } else {
                high = middle - 1;
            }
        }
        return new int[] {-1, -1};
    }
}
