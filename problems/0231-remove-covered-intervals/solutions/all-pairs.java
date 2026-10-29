public class Solution {
    public int removeCoveredIntervals(int[][] intervals) {
        int remaining = 0;
        for (int i = 0; i < intervals.length; i++) {
            if (!isCovered(intervals, i)) {
                remaining++;
            }
        }
        return remaining;
    }

    private static boolean isCovered(int[][] intervals, int i) {
        for (int j = 0; j < intervals.length; j++) {
            // The interval itself would cover itself, so skip j == i.
            if (j != i && intervals[j][0] <= intervals[i][0] && intervals[i][1] <= intervals[j][1]) {
                return true;
            }
        }
        return false;
    }
}
