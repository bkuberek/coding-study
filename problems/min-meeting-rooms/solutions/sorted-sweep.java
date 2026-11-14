import java.util.*;

public class Solution {
    public int minMeetingRooms(int[][] intervals) {
        int[] starts = new int[intervals.length];
        int[] ends = new int[intervals.length];
        for (int i = 0; i < intervals.length; i++) {
            starts[i] = intervals[i][0];
            ends[i] = intervals[i][1];
        }
        Arrays.sort(starts);
        Arrays.sort(ends);
        int rooms = 0;
        int ended = 0;
        for (int start : starts) {
            if (ends[ended] <= start) {
                // Some meeting has ended by now: its room is reused.
                ended++;
            } else {
                rooms++;
            }
        }
        return rooms;
    }
}
