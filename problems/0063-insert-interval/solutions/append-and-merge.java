import java.util.*;

public class Solution {
    public int[][] insert(int[][] intervals, int[] newInterval) {
        int[][] all = Arrays.copyOf(intervals, intervals.length + 1);
        all[intervals.length] = newInterval;
        Arrays.sort(all, Comparator.comparingInt(interval -> interval[0]));
        List<int[]> merged = new ArrayList<>();
        for (int[] interval : all) {
            int[] last = merged.isEmpty() ? null : merged.get(merged.size() - 1);
            if (last != null && interval[0] <= last[1]) {
                last[1] = Math.max(last[1], interval[1]);
            } else {
                merged.add(new int[] {interval[0], interval[1]});
            }
        }
        return merged.toArray(new int[0][]);
    }
}
