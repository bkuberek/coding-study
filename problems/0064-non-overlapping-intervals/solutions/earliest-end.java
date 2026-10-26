import java.util.*;

public class Solution {
    public int eraseOverlapIntervals(int[][] intervals) {
        int[][] byEnd = intervals.clone();
        Arrays.sort(byEnd, Comparator.comparingInt(interval -> interval[1]));
        int kept = 0;
        long lastEnd = Long.MIN_VALUE;
        for (int[] interval : byEnd) {
            if (interval[0] >= lastEnd) {
                kept++;
                lastEnd = interval[1];
            }
        }
        return intervals.length - kept;
    }
}
