import java.util.*;

public class Solution {
    public int[][] employeeFreeTime(List<List<int[]>> schedule) {
        // One entry per employee: the start of their next interval, who they are, and its position.
        PriorityQueue<int[]> upcoming = new PriorityQueue<>(
                Comparator.comparingInt((int[] entry) -> entry[0]).thenComparingInt(entry -> entry[1]));
        for (int person = 0; person < schedule.size(); person++) {
            upcoming.add(new int[] {schedule.get(person).get(0)[0], person, 0});
        }
        List<int[]> free = new ArrayList<>();
        int busyUntil = upcoming.peek()[0];
        while (!upcoming.isEmpty()) {
            int[] entry = upcoming.poll();
            int start = entry[0];
            int person = entry[1];
            int position = entry[2];
            List<int[]> shifts = schedule.get(person);
            if (start > busyUntil) {
                free.add(new int[] {busyUntil, start});
            }
            busyUntil = Math.max(busyUntil, shifts.get(position)[1]);
            if (position + 1 < shifts.size()) {
                upcoming.add(new int[] {shifts.get(position + 1)[0], person, position + 1});
            }
        }
        return free.toArray(new int[0][]);
    }
}
