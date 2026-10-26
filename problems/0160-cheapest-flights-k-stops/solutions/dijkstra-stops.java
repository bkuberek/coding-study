import java.util.*;

public class Solution {
    public int findCheapestPrice(int n, int[][] flights, int src, int dst, int k) {
        List<List<int[]>> graph = new ArrayList<>();
        for (int city = 0; city < n; city++) {
            graph.add(new ArrayList<>());
        }
        for (int[] flight : flights) {
            graph.get(flight[0]).add(new int[] {flight[1], flight[2]});
        }
        // fewest[c] is the fewest flights with which c was settled so far. States leave the heap
        // in order of price, so a later state for c is useful only if it used fewer flights.
        int[] fewest = new int[n];
        Arrays.fill(fewest, k + 2);
        // States are {price, city, used}.
        PriorityQueue<int[]> heap = new PriorityQueue<>(Comparator.comparingInt(state -> state[0]));
        heap.add(new int[] {0, src, 0});
        while (!heap.isEmpty()) {
            int[] state = heap.poll();
            int price = state[0];
            int city = state[1];
            int used = state[2];
            if (city == dst) {
                return price;
            }
            if (used >= fewest[city]) {
                continue;
            }
            fewest[city] = used;
            if (used == k + 1) {
                continue; // no flights left
            }
            for (int[] edge : graph.get(city)) {
                heap.add(new int[] {price + edge[1], edge[0], used + 1});
            }
        }
        return -1;
    }
}
