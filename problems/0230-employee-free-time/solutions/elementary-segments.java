import java.util.*;

public class Solution {
    public int[][] employeeFreeTime(List<List<int[]>> schedule) {
        List<int[]> intervals = new ArrayList<>();
        for (List<int[]> shifts : schedule) {
            intervals.addAll(shifts);
        }
        TreeSet<Integer> endpoints = new TreeSet<>();
        for (int[] interval : intervals) {
            endpoints.add(interval[0]);
            endpoints.add(interval[1]);
        }
        List<Integer> points = new ArrayList<>(endpoints);
        List<int[]> free = new ArrayList<>();
        for (int i = 1; i < points.size(); i++) {
            int left = points.get(i - 1);
            // No interval starts or ends strictly inside (left, right): it is all busy or all free.
            if (!isBusyAt(intervals, left)) {
                free.add(new int[] {left, points.get(i)});
            }
        }
        return free.toArray(new int[0][]);
    }

    private static boolean isBusyAt(List<int[]> intervals, int moment) {
        for (int[] interval : intervals) {
            if (interval[0] <= moment && moment < interval[1]) {
                return true;
            }
        }
        return false;
    }
}
