import java.util.*;

public class Solution {
    // Reduced components lie in [-2 * 10^4, 2 * 10^4], so this packs a direction into one long.
    private static final long KEY_BASE = 100_000L;

    public int maxPoints(int[][] points) {
        int best = 1;
        for (int i = 0; i < points.length; i++) {
            Map<Long, Integer> directions = new HashMap<>();
            int most = 0;
            for (int j = i + 1; j < points.length; j++) {
                int dx = points[j][0] - points[i][0];
                int dy = points[j][1] - points[i][1];
                int divisor = gcd(Math.abs(dx), Math.abs(dy)); // never 0: the points are distinct
                dx /= divisor;
                dy /= divisor;
                // One representative per direction: dx > 0, or dx == 0 and dy > 0.
                if (dx < 0 || (dx == 0 && dy < 0)) {
                    dx = -dx;
                    dy = -dy;
                }
                int count = directions.merge(dx * KEY_BASE + dy, 1, Integer::sum);
                most = Math.max(most, count);
            }
            best = Math.max(best, most + 1); // + 1 for the anchor
        }
        return best;
    }

    private static int gcd(int a, int b) {
        while (b != 0) {
            int rest = a % b;
            a = b;
            b = rest;
        }
        return a;
    }
}
