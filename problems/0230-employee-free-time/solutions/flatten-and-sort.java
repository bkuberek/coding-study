import java.util.*;

public class Solution {
    public int[][] employeeFreeTime(List<List<int[]>> schedule) {
        List<int[]> intervals = new ArrayList<>();
        for (List<int[]> shifts : schedule) {
            intervals.addAll(shifts);
        }
        intervals.sort(Comparator.comparingInt(interval -> interval[0]));
        List<int[]> free = new ArrayList<>();
        int busyUntil = intervals.get(0)[1];
        for (int[] interval : intervals) {
            if (interval[0] > busyUntil) {
                free.add(new int[] {busyUntil, interval[0]});
            }
            busyUntil = Math.max(busyUntil, interval[1]);
        }
        return free.toArray(new int[0][]);
    }
}
