public class NumArray {
    private final int[] values;
    // tree[i] (1-based) holds the sum of the i & -i values ending at position i - 1.
    private final long[] tree;

    public NumArray(int[] nums) {
        values = nums.clone();
        tree = new long[nums.length + 1];
        for (int i = 1; i <= nums.length; i++) {
            tree[i] += nums[i - 1];
            int parent = i + (i & -i);
            if (parent <= nums.length) {
                tree[parent] += tree[i];
            }
        }
    }

    public void update(int index, int value) {
        long delta = (long) value - values[index];
        values[index] = value;
        for (int i = index + 1; i < tree.length; i += i & -i) {
            tree[i] += delta;
        }
    }

    public long sumRange(int left, int right) {
        return prefix(right + 1) - prefix(left);
    }

    /** Sum of the first count values. */
    private long prefix(int count) {
        long total = 0;
        for (int i = count; i > 0; i -= i & -i) {
            total += tree[i];
        }
        return total;
    }
}
