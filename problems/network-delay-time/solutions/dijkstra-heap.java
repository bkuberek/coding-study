import java.util.*;

public class Solution {
    public int networkDelayTime(int[][] times, int n, int k) {
        List<List<int[]>> graph = new ArrayList<>();
        for (int node = 0; node <= n; node++) {
            graph.add(new ArrayList<>());
        }
        for (int[] link : times) {
            graph.get(link[0]).add(new int[] {link[1], link[2]});
        }
        int[] arrival = new int[n + 1];
        Arrays.fill(arrival, -1);
        // Entries are {time, node}; PriorityQueue is a min-heap under this comparator.
        PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(entry -> entry[0]));
        heap.add(new int[] {0, k});
        int settled = 0;
        int latest = 0;
        while (!heap.isEmpty()) {
            int[] entry = heap.poll();
            int time = entry[0];
            int node = entry[1];
            if (arrival[node] != -1) {
                continue; // an outdated entry: settled earlier with a smaller time
            }
            arrival[node] = time;
            settled++;
            latest = time;
            for (int[] edge : graph.get(node)) {
                if (arrival[edge[0]] == -1) {
                    heap.add(new int[] {time + edge[1], edge[0]});
                }
            }
        }
        return settled == n ? latest : -1;
    }
}
