import java.util.*;

public class Solution {
    public int jobScheduling(int[] startTime, int[] endTime, int[] profit) {
        int n = startTime.length;
        // Each row is {end, start, profit}; sorted by end time.
        int[][] jobs = new int[n][];
        for (int job = 0; job < n; job++) {
            jobs[job] = new int[] {endTime[job], startTime[job], profit[job]};
        }
        Arrays.sort(jobs, Comparator.comparingInt(row -> row[0]));
        // best[i] is the most profit from the first i jobs in end-time order.
        int[] best = new int[n + 1];
        for (int i = 0; i < n; i++) {
            int start = jobs[i][1];
            // Upper bound: how many of the first i jobs end no later than this one starts.
            int low = 0;
            int high = i;
            while (low < high) {
                int middle = (low + high) >>> 1;
                if (jobs[middle][0] <= start) {
                    low = middle + 1;
                } else {
                    high = middle;
                }
            }
            best[i + 1] = Math.max(best[i], jobs[i][2] + best[low]);
        }
        return best[n];
    }
}
