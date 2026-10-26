import java.util.*;

public class Solution {
    public int lastStoneWeight(int[] stones) {
        // PriorityQueue is a min-heap; the reversed comparator turns it into a max-heap.
        PriorityQueue<Integer> heap = new PriorityQueue<>(Math.max(1, stones.length), Comparator.reverseOrder());
        for (int weight : stones) {
            heap.offer(weight);
        }
        while (heap.size() > 1) {
            int heaviest = heap.poll();
            int second = heap.poll();
            if (heaviest != second) {
                heap.offer(heaviest - second);
            }
        }
        return heap.isEmpty() ? 0 : heap.peek();
    }
}
