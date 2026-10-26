import java.util.*;

public class Solution {
    private static final int UNREACHED = Integer.MAX_VALUE;

    public int networkDelayTime(int[][] times, int n, int k) {
        int[] arrival = new int[n + 1];
        Arrays.fill(arrival, UNREACHED);
        arrival[k] = 0;
        // After round i, every node whose fastest route uses at most i links has its final time;
        // a fastest route has at most n - 1 links, and a round without changes ends early.
        for (int round = 1; round < n; round++) {
            boolean changed = false;
            for (int[] link : times) {
                int u = link[0];
                int v = link[1];
                if (arrival[u] != UNREACHED && arrival[u] + link[2] < arrival[v]) {
                    arrival[v] = arrival[u] + link[2];
                    changed = true;
                }
            }
            if (!changed) {
                break;
            }
        }
        int latest = 0;
        for (int node = 1; node <= n; node++) {
            latest = Math.max(latest, arrival[node]);
        }
        return latest == UNREACHED ? -1 : latest;
    }
}
