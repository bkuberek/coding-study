public class NumArray {
    private final int[] nums;

    public NumArray(int[] nums) {
        this.nums = nums;
    }

    public long sumRange(int left, int right) {
        long total = 0;
        for (int i = left; i <= right; i++) {
            total += nums[i];
        }
        return total;
    }
}
