import java.util.*;

public class Solution {
    // A pair is packed into one long: cost << 20 | i << 10 | j, so sorting longs sorts by cost.
    private static final int INDEX_BITS = 10;
    private static final long INDEX_MASK = (1L << INDEX_BITS) - 1;

    public int minCostConnectPoints(int[][] points) {
        int n = points.length;
        long[] pairs = new long[n * (n - 1) / 2];
        int next = 0;
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                long cost = Math.abs(points[i][0] - points[j][0]) + Math.abs(points[i][1] - points[j][1]);
                pairs[next++] = (cost << (2 * INDEX_BITS)) | ((long) i << INDEX_BITS) | j;
            }
        }
        Arrays.sort(pairs);

        int[] parent = new int[n];
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
        int total = 0;
        int cables = 0;
        // Take pairs from cheapest to most expensive, keeping each one that joins two groups.
        for (int index = 0; index < pairs.length && cables < n - 1; index++) {
            long packed = pairs[index];
            int j = (int) (packed & INDEX_MASK);
            int i = (int) ((packed >> INDEX_BITS) & INDEX_MASK);
            int rootI = find(parent, i);
            int rootJ = find(parent, j);
            if (rootI != rootJ) {
                parent[rootI] = rootJ;
                total += (int) (packed >> (2 * INDEX_BITS));
                cables++;
            }
        }
        return total;
    }

    private static int find(int[] parent, int node) {
        int root = node;
        while (parent[root] != root) {
            root = parent[root];
        }
        while (parent[node] != root) {
            int up = parent[node];
            parent[node] = root;
            node = up;
        }
        return root;
    }
}
