import java.util.*;

public class Solution {
    public int[] getOrder(int[][] tasks) {
        int n = tasks.length;
        Integer[] arrivals = new Integer[n];
        for (int index = 0; index < n; index++) {
            arrivals[index] = index;
        }
        Arrays.sort(arrivals, Comparator.comparingInt(index -> tasks[index][0]));
        // Waiting tasks by processing time, then by index.
        PriorityQueue<Integer> waiting = new PriorityQueue<>(
                Comparator.<Integer>comparingInt(index -> tasks[index][1]).thenComparingInt(index -> index));
        int[] order = new int[n];
        long time = 0; // a sum of processing times can pass Integer.MAX_VALUE
        int next = 0;
        for (int picked = 0; picked < n; picked++) {
            if (waiting.isEmpty() && time < tasks[arrivals[next]][0]) {
                time = tasks[arrivals[next]][0]; // idle until the next arrival
            }
            while (next < n && tasks[arrivals[next]][0] <= time) {
                waiting.offer(arrivals[next++]);
            }
            int index = waiting.poll();
            time += tasks[index][1];
            order[picked] = index;
        }
        return order;
    }
}
