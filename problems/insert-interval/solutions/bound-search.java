import java.util.*;
import java.util.function.*;

public class Solution {
    public int[][] insert(int[][] intervals, int[] newInterval) {
        int start = newInterval[0];
        int end = newInterval[1];
        // Separate sorted intervals have increasing starts and increasing ends.
        int first = firstIndex(intervals, interval -> interval[1] >= newInterval[0]);
        int after = firstIndex(intervals, interval -> interval[0] > newInterval[1]);
        if (first < after) {
            start = Math.min(start, intervals[first][0]);
            end = Math.max(end, intervals[after - 1][1]);
        }
        int[][] result = new int[first + 1 + intervals.length - after][];
        System.arraycopy(intervals, 0, result, 0, first);
        result[first] = new int[] {start, end};
        System.arraycopy(intervals, after, result, first + 1, intervals.length - after);
        return result;
    }

    private static int firstIndex(int[][] intervals, Predicate<int[]> isPast) {
        int low = 0;
        int high = intervals.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (isPast.test(intervals[middle])) {
                high = middle;
            } else {
                low = middle + 1;
            }
        }
        return low;
    }
}
