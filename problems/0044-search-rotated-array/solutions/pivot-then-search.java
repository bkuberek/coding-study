public class Solution {
    public int search(int[] nums, int target) {
        int pivot = indexOfMinimum(nums);
        int last = nums.length - 1;
        if (nums[pivot] <= target && target <= nums[last]) {
            return binarySearch(nums, target, pivot, last);
        }
        return binarySearch(nums, target, 0, pivot - 1);
    }

    private static int indexOfMinimum(int[] nums) {
        int low = 0;
        int high = nums.length - 1;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (nums[middle] > nums[high]) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }

    private static int binarySearch(int[] nums, int target, int low, int high) {
        while (low <= high) {
            int middle = (low + high) >>> 1;
            if (nums[middle] == target) {
                return middle;
            }
            if (nums[middle] < target) {
                low = middle + 1;
            } else {
                high = middle - 1;
            }
        }
        return -1;
    }
}
