public class NumArray {
    // prefix[i] is the sum of nums[0..i-1]; long because a sum can pass 2^31.
    private final long[] prefix;

    public NumArray(int[] nums) {
        prefix = new long[nums.length + 1];
        for (int i = 0; i < nums.length; i++) {
            prefix[i + 1] = prefix[i] + nums[i];
        }
    }

    public long sumRange(int left, int right) {
        return prefix[right + 1] - prefix[left];
    }
}
