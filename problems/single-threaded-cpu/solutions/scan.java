import java.util.*;

public class Solution {
    public int[] getOrder(int[][] tasks) {
        int n = tasks.length;
        boolean[] done = new boolean[n];
        int[] order = new int[n];
        long time = 0; // a sum of processing times can pass Integer.MAX_VALUE
        for (int picked = 0; picked < n; ) {
            // Scan every waiting task; a strict < keeps the smaller index on equal times.
            int best = -1;
            long nextArrival = Long.MAX_VALUE;
            for (int index = 0; index < n; index++) {
                if (done[index]) {
                    continue;
                }
                if (tasks[index][0] <= time) {
                    if (best < 0 || tasks[index][1] < tasks[best][1]) {
                        best = index;
                    }
                } else {
                    nextArrival = Math.min(nextArrival, tasks[index][0]);
                }
            }
            if (best < 0) {
                time = nextArrival; // idle until the next arrival
                continue;
            }
            done[best] = true;
            time += tasks[best][1];
            order[picked++] = best;
        }
        return order;
    }
}
