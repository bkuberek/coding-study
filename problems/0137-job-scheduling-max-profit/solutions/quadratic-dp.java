import java.util.*;

public class Solution {
    public int jobScheduling(int[] startTime, int[] endTime, int[] profit) {
        int n = startTime.length;
        Integer[] order = new Integer[n];
        for (int job = 0; job < n; job++) {
            order[job] = job;
        }
        Arrays.sort(order, Comparator.comparingInt(job -> endTime[job]));
        // best[i] is the most profit from the first i jobs in end-time order.
        int[] best = new int[n + 1];
        for (int i = 0; i < n; i++) {
            int job = order[i];
            // Walk back to the last job that ends no later than this one starts.
            int compatible = i - 1;
            while (compatible >= 0 && endTime[order[compatible]] > startTime[job]) {
                compatible--;
            }
            best[i + 1] = Math.max(best[i], profit[job] + best[compatible + 1]);
        }
        return best[n];
    }
}
