import java.util.*;

public class Solution {
    public int mincostTickets(int[] days, int[] costs) {
        int lastDay = days[days.length - 1];
        boolean[] travel = new boolean[lastDay + 1];
        for (int day : days) {
            travel[day] = true;
        }
        // cost[d] is the cheapest way to cover every trip on calendar days 1..d.
        int[] cost = new int[lastDay + 1];
        for (int d = 1; d <= lastDay; d++) {
            if (!travel[d]) {
                cost[d] = cost[d - 1];
                continue;
            }
            int dayPass = cost[d - 1] + costs[0];
            int weekPass = cost[Math.max(0, d - 7)] + costs[1];
            int monthPass = cost[Math.max(0, d - 30)] + costs[2];
            cost[d] = Math.min(dayPass, Math.min(weekPass, monthPass));
        }
        return cost[lastDay];
    }
}
