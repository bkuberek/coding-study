import java.util.*;

public class Solution {
    public int eraseOverlapIntervals(int[][] intervals) {
        int[][] ordered = intervals.clone();
        Arrays.sort(ordered, Comparator.<int[]>comparingInt(interval -> interval[0]).thenComparingInt(interval -> interval[1]));
        // longest[i]: the most intervals that can be kept among ordered[0..i], ending with ordered[i].
        int[] longest = new int[ordered.length];
        int kept = 0;
        for (int i = 0; i < ordered.length; i++) {
            int best = 0;
            for (int j = 0; j < i; j++) {
                if (ordered[j][1] <= ordered[i][0]) {
                    best = Math.max(best, longest[j]);
                }
            }
            longest[i] = best + 1;
            kept = Math.max(kept, longest[i]);
        }
        return intervals.length - kept;
    }
}
