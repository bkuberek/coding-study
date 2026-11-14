import java.util.*;

public class Solution {
    public int findTheCity(int n, int[][] edges, int distanceThreshold) {
        List<List<int[]>> graph = new ArrayList<>();
        for (int city = 0; city < n; city++) {
            graph.add(new ArrayList<>());
        }
        for (int[] edge : edges) {
            graph.get(edge[0]).add(new int[] {edge[1], edge[2]});
            graph.get(edge[1]).add(new int[] {edge[0], edge[2]});
        }
        int bestCity = -1;
        int bestCount = n + 1;
        for (int city = 0; city < n; city++) {
            int count = reachable(graph, city, distanceThreshold);
            // `<=` lets a later city win a tie.
            if (count <= bestCount) {
                bestCity = city;
                bestCount = count;
            }
        }
        return bestCity;
    }

    /** Counts the other cities within the threshold, never pushing a distance beyond it. */
    private int reachable(List<List<int[]>> graph, int source, int threshold) {
        boolean[] settled = new boolean[graph.size()];
        // Entries are {distance, city}.
        PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(entry -> entry[0]));
        heap.add(new int[] {0, source});
        int count = -1;
        while (!heap.isEmpty()) {
            int[] entry = heap.poll();
            int city = entry[1];
            if (settled[city]) {
                continue;
            }
            settled[city] = true;
            count++;
            for (int[] road : graph.get(city)) {
                if (!settled[road[0]] && entry[0] + road[1] <= threshold) {
                    heap.add(new int[] {entry[0] + road[1], road[0]});
                }
            }
        }
        return count;
    }
}
