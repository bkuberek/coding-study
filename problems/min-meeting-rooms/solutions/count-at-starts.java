public class Solution {
    public int minMeetingRooms(int[][] intervals) {
        // The busiest moment is always the start of some meeting.
        int rooms = 0;
        for (int[] meeting : intervals) {
            int moment = meeting[0];
            int running = 0;
            for (int[] other : intervals) {
                if (other[0] <= moment && moment < other[1]) {
                    running++;
                }
            }
            rooms = Math.max(rooms, running);
        }
        return rooms;
    }
}
