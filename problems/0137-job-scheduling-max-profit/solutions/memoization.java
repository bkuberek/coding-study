import java.util.*;

public class Solution {
    private int[][] jobs;
    private int[] memo;

    public int jobScheduling(int[] startTime, int[] endTime, int[] profit) {
        int n = startTime.length;
        // Each row is {start, end, profit}; sorted by start time.
        jobs = new int[n][];
        for (int job = 0; job < n; job++) {
            jobs[job] = new int[] {startTime[job], endTime[job], profit[job]};
        }
        Arrays.sort(jobs, Comparator.comparingInt(row -> row[0]));
        // memo[index] is the most profit from the jobs at sorted positions index..n-1, or -1.
        memo = new int[n];
        Arrays.fill(memo, -1);
        return bestFrom(0);
    }

    private int bestFrom(int index) {
        if (index == jobs.length) {
            return 0;
        }
        if (memo[index] == -1) {
            int following = firstStartingAt(jobs[index][1], index + 1);
            memo[index] = Math.max(bestFrom(index + 1), jobs[index][2] + bestFrom(following));
        }
        return memo[index];
    }

    /** The first position at or after {@code from} whose start is at least {@code time}. */
    private int firstStartingAt(int time, int from) {
        int low = from;
        int high = jobs.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (jobs[middle][0] < time) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
