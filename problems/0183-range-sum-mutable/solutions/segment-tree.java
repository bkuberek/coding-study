public class NumArray {
    private final int size;
    // Leaves at size .. 2 * size - 1; node i holds the sum of its children 2i and 2i + 1.
    private final long[] tree;

    public NumArray(int[] nums) {
        size = nums.length;
        tree = new long[2 * size];
        for (int i = 0; i < size; i++) {
            tree[size + i] = nums[i];
        }
        for (int node = size - 1; node > 0; node--) {
            tree[node] = tree[2 * node] + tree[2 * node + 1];
        }
    }

    public void update(int index, int value) {
        int node = index + size;
        tree[node] = value;
        while (node > 1) {
            node >>= 1;
            tree[node] = tree[2 * node] + tree[2 * node + 1];
        }
    }

    public long sumRange(int left, int right) {
        long total = 0;
        // Half-open [low, high) over the leaves, narrowed one level per round.
        int low = left + size;
        int high = right + size + 1;
        while (low < high) {
            if ((low & 1) == 1) {
                total += tree[low++];
            }
            if ((high & 1) == 1) {
                total += tree[--high];
            }
            low >>= 1;
            high >>= 1;
        }
        return total;
    }
}
