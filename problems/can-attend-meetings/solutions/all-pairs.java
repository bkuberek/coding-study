public class Solution {
    public boolean canAttendMeetings(int[][] intervals) {
        for (int i = 0; i < intervals.length; i++) {
            for (int j = i + 1; j < intervals.length; j++) {
                // Half-open meetings share a moment exactly when each starts before the other ends.
                if (intervals[i][0] < intervals[j][1] && intervals[j][0] < intervals[i][1]) {
                    return false;
                }
            }
        }
        return true;
    }
}
