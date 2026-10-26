import java.util.concurrent.ThreadLocalRandom;

public class Solution {
    public int findKthLargest(int[] nums, int k) {
        int[] values = nums.clone();
        int target = values.length - k; // the answer's index in ascending order
        int low = 0;
        int high = values.length - 1;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        while (true) {
            int pivot = values[random.nextInt(low, high + 1)];
            // Three-way partition of values[low..high]: < pivot | == pivot | > pivot.
            int less = low;
            int scan = low;
            int greater = high;
            while (scan <= greater) {
                if (values[scan] < pivot) {
                    swap(values, less++, scan++);
                } else if (values[scan] > pivot) {
                    swap(values, scan, greater--);
                } else {
                    scan++;
                }
            }
            if (target < less) {
                high = less - 1;
            } else if (target > greater) {
                low = greater + 1;
            } else {
                return pivot;
            }
        }
    }

    private static void swap(int[] values, int i, int j) {
        int held = values[i];
        values[i] = values[j];
        values[j] = held;
    }
}
