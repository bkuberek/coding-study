import java.util.*;

public class Solution {
    private static final long MODULUS = 1_000_000_007L;

    public int createSortedArray(int[] instructions) {
        ArrayList<Integer> ordered = new ArrayList<>();
        long cost = 0; // a long: the total can pass 2^31 - 1 before the final reduction
        for (int value : instructions) {
            int less = countBelow(ordered, value, false);
            int lessOrEqual = countBelow(ordered, value, true);
            cost += Math.min(less, ordered.size() - lessOrEqual);
            ordered.add(lessOrEqual, value);
        }
        return (int) (cost % MODULUS);
    }

    /** How many values of the sorted list are below target (or at most target, if inclusive). */
    private static int countBelow(List<Integer> sorted, int target, boolean inclusive) {
        int low = 0;
        int high = sorted.size();
        while (low < high) {
            int middle = low + (high - low) / 2;
            int value = sorted.get(middle);
            if (value < target || (inclusive && value == target)) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
