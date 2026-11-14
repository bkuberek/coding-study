import java.util.*;

public class Solution {
    public int[][] merge(int[][] intervals) {
        List<int[]> merged = new ArrayList<>();
        for (int[] interval : intervals) {
            int start = interval[0];
            int end = interval[1];
            // Fold every merged interval that shares a point with [start, end] into it.
            List<int[]> separate = new ArrayList<>();
            for (int[] other : merged) {
                if (other[0] <= end && start <= other[1]) {
                    start = Math.min(start, other[0]);
                    end = Math.max(end, other[1]);
                } else {
                    separate.add(other);
                }
            }
            separate.add(new int[] {start, end});
            merged = separate;
        }
        return merged.toArray(new int[0][]);
    }
}
