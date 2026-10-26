import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

public class Solution {
    public int[][] kClosest(int[][] points, int k) {
        int n = points.length;
        int[] distance = new int[n];
        int[] order = new int[n];
        for (int index = 0; index < n; index++) {
            distance[index] = points[index][0] * points[index][0] + points[index][1] * points[index][1];
            order[index] = index;
        }
        int low = 0;
        int high = n - 1;
        ThreadLocalRandom random = ThreadLocalRandom.current();
        // Partition until position k - 1 holds its sorted entry; then positions 0..k-1 hold
        // the k closest points (in some order).
        while (low < high) {
            int pivot = distance[order[random.nextInt(low, high + 1)]];
            int less = low;
            int scan = low;
            int greater = high;
            while (scan <= greater) {
                int value = distance[order[scan]];
                if (value < pivot) {
                    swap(order, less++, scan++);
                } else if (value > pivot) {
                    swap(order, scan, greater--);
                } else {
                    scan++;
                }
            }
            if (k - 1 < less) {
                high = less - 1;
            } else if (k - 1 > greater) {
                low = greater + 1;
            } else {
                break;
            }
        }
        int[][] closest = new int[k][];
        for (int slot = 0; slot < k; slot++) {
            closest[slot] = points[order[slot]];
        }
        return closest;
    }

    private static void swap(int[] values, int i, int j) {
        int held = values[i];
        values[i] = values[j];
        values[j] = held;
    }
}
