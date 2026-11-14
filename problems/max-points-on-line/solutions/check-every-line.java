public class Solution {
    public int maxPoints(int[][] points) {
        int n = points.length;
        if (n <= 2) {
            return n;
        }
        int best = 2;
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                int dx = points[j][0] - points[i][0];
                int dy = points[j][1] - points[i][1];
                // (x, y) is on the line through both points when the cross product is zero.
                // Each factor is at most 2 * 10^4 in absolute value, so the products fit in an int.
                int onLine = 0;
                for (int[] point : points) {
                    if (dy * (point[0] - points[i][0]) == dx * (point[1] - points[i][1])) {
                        onLine++;
                    }
                }
                best = Math.max(best, onLine);
            }
        }
        return best;
    }
}
