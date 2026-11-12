import java.util.*;

public class KthLargestTracker {
    private final int k;
    private final List<Integer> values = new ArrayList<>(); // every number so far, ascending

    public KthLargestTracker(int k, int[] nums) {
        this.k = k;
        int[] sorted = nums.clone();
        Arrays.sort(sorted);
        for (int value : sorted) {
            values.add(value);
        }
    }

    public int add(int value) {
        // binarySearch returns -(insertion point) - 1 when the value is absent.
        int index = Collections.binarySearch(values, value);
        values.add(index >= 0 ? index : -index - 1, value);
        // The kth largest is the kth entry from the end.
        return values.get(values.size() - k);
    }
}
