import java.util.*;

public class Solution {
    public int[][] merge(int[][] intervals) {
        int[][] sorted = intervals.clone();
        Arrays.sort(sorted, Comparator.comparingInt(interval -> interval[0]));
        List<int[]> merged = new ArrayList<>();
        for (int[] interval : sorted) {
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
