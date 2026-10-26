import java.util.*;

public class Solution {
    public int minMeetingRooms(int[][] intervals) {
        int[][] byStart = intervals.clone();
        Arrays.sort(byStart, Comparator.comparingInt(meeting -> meeting[0]));
        // End times of the meetings currently holding a room; the smallest is on top.
        PriorityQueue<Integer> ends = new PriorityQueue<>();
        for (int[] meeting : byStart) {
            if (!ends.isEmpty() && ends.peek() <= meeting[0]) {
                ends.poll();
            }
            ends.offer(meeting[1]);
        }
        return ends.size();
    }
}
