import java.util.*;

public class Solution {
    public boolean canAttendMeetings(int[][] intervals) {
        int[][] ordered = intervals.clone();
        Arrays.sort(ordered, Comparator.comparingInt(meeting -> meeting[0]));
        // After sorting by start, only neighbors can be the first clash.
        for (int i = 1; i < ordered.length; i++) {
            if (ordered[i - 1][1] > ordered[i][0]) {
                return false;
            }
        }
        return true;
    }
}
