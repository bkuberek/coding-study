import java.util.*;

public class Solution {
    public int findMaximizedCapital(int k, int w, int[] profits, int[] capital) {
        int n = profits.length;
        int[][] projects = new int[n][];
        for (int index = 0; index < n; index++) {
            projects[index] = new int[] {capital[index], profits[index]};
        }
        Arrays.sort(projects, Comparator.comparingInt(project -> project[0])); // cheapest first
        PriorityQueue<Integer> affordable = new PriorityQueue<>(Comparator.reverseOrder());
        int unlocked = 0;
        for (int round = 0; round < k; round++) {
            // Capital only grows, so every project unlocked once stays affordable.
            while (unlocked < n && projects[unlocked][0] <= w) {
                affordable.offer(projects[unlocked++][1]);
            }
            if (affordable.isEmpty()) {
                break; // nothing affordable now, and capital cannot grow any more
            }
            w += affordable.poll();
        }
        return w;
    }
}
