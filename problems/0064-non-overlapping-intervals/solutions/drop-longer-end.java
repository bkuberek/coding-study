import java.util.*;

public class Solution {
    public int eraseOverlapIntervals(int[][] intervals) {
        int[][] ordered = intervals.clone();
        Arrays.sort(ordered, Comparator.comparingInt(interval -> interval[0]));
        int removed = 0;
        int keptEnd = ordered[0][1];
        for (int i = 1; i < ordered.length; i++) {
            if (ordered[i][0] < keptEnd) {
                // Conflict: keep whichever of the two ends first.
                removed++;
                keptEnd = Math.min(keptEnd, ordered[i][1]);
            } else {
                keptEnd = ordered[i][1];
            }
        }
        return removed;
    }
}
