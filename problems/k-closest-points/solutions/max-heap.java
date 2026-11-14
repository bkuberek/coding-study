import java.util.*;

public class Solution {
    public int[][] kClosest(int[][] points, int k) {
        // Entries are {squared distance, index}; the reversed order makes the head the
        // farthest of the k closest points kept so far.
        PriorityQueue<int[]> heap = new PriorityQueue<>((a, b) -> Integer.compare(b[0], a[0]));
        for (int index = 0; index < points.length; index++) {
            int x = points[index][0];
            int y = points[index][1];
            int distance = x * x + y * y;
            if (heap.size() < k) {
                heap.offer(new int[] {distance, index});
            } else if (distance < heap.peek()[0]) {
                heap.poll();
                heap.offer(new int[] {distance, index});
            }
        }
        int[][] closest = new int[heap.size()][];
        int slot = 0;
        for (int[] entry : heap) {
            closest[slot++] = points[entry[1]];
        }
        return closest;
    }
}
