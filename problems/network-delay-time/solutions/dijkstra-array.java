import java.util.*;

public class Solution {
    private static final int UNREACHED = Integer.MAX_VALUE;

    public int networkDelayTime(int[][] times, int n, int k) {
        List<List<int[]>> graph = new ArrayList<>();
        for (int node = 0; node <= n; node++) {
            graph.add(new ArrayList<>());
        }
        for (int[] link : times) {
            graph.get(link[0]).add(new int[] {link[1], link[2]});
        }
        int[] arrival = new int[n + 1];
        Arrays.fill(arrival, UNREACHED);
        arrival[k] = 0;
        boolean[] settled = new boolean[n + 1];
        int latest = 0;
        for (int round = 0; round < n; round++) {
            // Scan for the unsettled node with the earliest arrival: O(n) per round, no heap.
            int node = -1;
            for (int v = 1; v <= n; v++) {
                if (!settled[v] && (node == -1 || arrival[v] < arrival[node])) {
                    node = v;
                }
            }
            if (arrival[node] == UNREACHED) {
                return -1;
            }
            settled[node] = true;
            latest = arrival[node];
            for (int[] edge : graph.get(node)) {
                arrival[edge[0]] = Math.min(arrival[edge[0]], arrival[node] + edge[1]);
            }
        }
        return latest;
    }
}
