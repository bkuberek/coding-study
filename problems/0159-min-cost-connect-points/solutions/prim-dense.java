import java.util.*;

public class Solution {
    public int minCostConnectPoints(int[][] points) {
        int n = points.length;
        // cheapest[i] is the cheapest cable from point i to the tree built so far.
        int[] cheapest = new int[n];
        Arrays.fill(cheapest, Integer.MAX_VALUE);
        boolean[] inTree = new boolean[n];
        cheapest[0] = 0;
        int total = 0;
        for (int round = 0; round < n; round++) {
            int point = -1;
            for (int i = 0; i < n; i++) {
                if (!inTree[i] && (point == -1 || cheapest[i] < cheapest[point])) {
                    point = i;
                }
            }
            inTree[point] = true;
            total += cheapest[point];
            for (int other = 0; other < n; other++) {
                if (!inTree[other]) {
                    int cost = Math.abs(points[point][0] - points[other][0])
                            + Math.abs(points[point][1] - points[other][1]);
                    cheapest[other] = Math.min(cheapest[other], cost);
                }
            }
        }
        return total;
    }
}
