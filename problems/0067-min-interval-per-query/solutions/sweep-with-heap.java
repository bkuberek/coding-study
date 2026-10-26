import java.util.*;

public class Solution {
    public int[] minInterval(int[][] intervals, int[] queries) {
        int[][] byLeft = intervals.clone();
        Arrays.sort(byLeft, Comparator.comparingInt(interval -> interval[0]));
        Integer[] order = new Integer[queries.length];
        for (int j = 0; j < queries.length; j++) {
            order[j] = j;
        }
        Arrays.sort(order, Comparator.comparingInt(j -> queries[j]));
        int[] answer = new int[queries.length];
        // Entries are {size, right} of intervals that start at or before the current query.
        PriorityQueue<int[]> candidates =
                new PriorityQueue<>(Comparator.<int[]>comparingInt(entry -> entry[0]).thenComparingInt(entry -> entry[1]));
        int added = 0;
        for (int index : order) {
            int query = queries[index];
            while (added < byLeft.length && byLeft[added][0] <= query) {
                int[] interval = byLeft[added++];
                candidates.offer(new int[] {interval[1] - interval[0] + 1, interval[1]});
            }
            // An interval that ends before this query also ends before every later one.
            while (!candidates.isEmpty() && candidates.peek()[1] < query) {
                candidates.poll();
            }
            answer[index] = candidates.isEmpty() ? -1 : candidates.peek()[0];
        }
        return answer;
    }
}
