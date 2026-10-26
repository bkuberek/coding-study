public class Solution {
    public int[] countSmaller(int[] nums) {
        int n = nums.length;
        int[] counts = new int[n];
        int[] order = new int[n]; // positions, sorted by value within each merged run
        for (int i = 0; i < n; i++) {
            order[i] = i;
        }
        int[] buffer = new int[n];
        // Bottom-up merge sort of positions by value; no recursion needed.
        for (int width = 1; width < n; width *= 2) {
            for (int low = 0; low < n; low += 2 * width) {
                int middle = Math.min(low + width, n);
                int high = Math.min(low + 2 * width, n);
                int left = low;
                int right = middle;
                int out = low;
                while (left < middle) {
                    if (right < high && nums[order[right]] < nums[order[left]]) {
                        buffer[out++] = order[right++];
                    } else {
                        // Every right-half element taken so far is smaller and came after it.
                        counts[order[left]] += right - middle;
                        buffer[out++] = order[left++];
                    }
                }
                while (right < high) {
                    buffer[out++] = order[right++];
                }
            }
            int[] swap = order;
            order = buffer;
            buffer = swap;
        }
        return counts;
    }
}
