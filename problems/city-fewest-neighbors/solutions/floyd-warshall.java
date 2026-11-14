import java.util.*;

public class Solution {
    // Large enough to never be a real distance, small enough that two of them do not overflow.
    private static final int FAR = Integer.MAX_VALUE / 2;

    public int findTheCity(int n, int[][] edges, int distanceThreshold) {
        int[][] dist = new int[n][n];
        for (int i = 0; i < n; i++) {
            Arrays.fill(dist[i], FAR);
            dist[i][i] = 0;
        }
        for (int[] edge : edges) {
            dist[edge[0]][edge[1]] = edge[2];
            dist[edge[1]][edge[0]] = edge[2];
        }
        // After step m, dist[i][j] is the shortest route that only passes through cities 0..m.
        for (int middle = 0; middle < n; middle++) {
            for (int i = 0; i < n; i++) {
                for (int j = 0; j < n; j++) {
                    dist[i][j] = Math.min(dist[i][j], dist[i][middle] + dist[middle][j]);
                }
            }
        }
        int bestCity = -1;
        int bestCount = n + 1;
        for (int city = 0; city < n; city++) {
            int count = 0;
            for (int other = 0; other < n; other++) {
                if (other != city && dist[city][other] <= distanceThreshold) {
                    count++;
                }
            }
            // `<=` lets a later city win a tie.
            if (count <= bestCount) {
                bestCity = city;
                bestCount = count;
            }
        }
        return bestCity;
    }
}
