import java.util.*;

public class Solution {
    private static final int WINDOW = 30;

    public int mincostTickets(int[] days, int[] costs) {
        // cost[d % WINDOW] holds the cheapest cover of days 1..d for the last 30 calendar days;
        // nothing older is ever read, because the longest pass lasts 30 days.
        int[] cost = new int[WINDOW];
        int lastDay = days[days.length - 1];
        int nextTrip = 0;
        for (int d = 1; d <= lastDay; d++) {
            int previous = cost[(d - 1) % WINDOW];
            if (d != days[nextTrip]) {
                cost[d % WINDOW] = previous;
                continue;
            }
            nextTrip++;
            int weekAgo = d >= 7 ? cost[(d - 7) % WINDOW] : 0;
            int monthAgo = d >= WINDOW ? cost[d % WINDOW] : 0;
            int best = Math.min(weekAgo + costs[1], monthAgo + costs[2]);
            cost[d % WINDOW] = Math.min(previous + costs[0], best);
        }
        return cost[lastDay % WINDOW];
    }
}
