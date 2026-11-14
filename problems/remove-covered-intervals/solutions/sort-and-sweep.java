import java.util.*;

public class Solution {
    public int removeCoveredIntervals(int[][] intervals) {
        int[][] ordered = intervals.clone();
        // Equal starts: the longer interval comes first, so it covers the shorter ones after it.
        Arrays.sort(
                ordered,
                (a, b) -> a[0] != b[0] ? Integer.compare(a[0], b[0]) : Integer.compare(b[1], a[1]));
        int remaining = 0;
        int reach = -1; // the largest end among the intervals already swept
        for (int[] interval : ordered) {
            if (interval[1] > reach) {
                remaining++;
                reach = interval[1];
            }
        }
        return remaining;
    }
}
