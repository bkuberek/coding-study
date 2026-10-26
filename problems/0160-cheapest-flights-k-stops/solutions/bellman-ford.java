import java.util.*;

public class Solution {
    private static final int UNREACHED = Integer.MAX_VALUE;

    public int findCheapestPrice(int n, int[][] flights, int src, int dst, int k) {
        // price[c] is the cheapest known price to reach c with at most `round` flights.
        int[] price = new int[n];
        Arrays.fill(price, UNREACHED);
        price[src] = 0;
        for (int round = 0; round <= k; round++) {
            // Read from the previous round only, so one round never chains two flights.
            int[] previous = price.clone();
            boolean changed = false;
            for (int[] flight : flights) {
                int start = flight[0];
                int end = flight[1];
                if (previous[start] != UNREACHED && previous[start] + flight[2] < price[end]) {
                    price[end] = previous[start] + flight[2];
                    changed = true;
                }
            }
            if (!changed) {
                break;
            }
        }
        return price[dst] == UNREACHED ? -1 : price[dst];
    }
}
