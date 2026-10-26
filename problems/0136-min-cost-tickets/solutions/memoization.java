import java.util.*;

public class Solution {
    private static final int[] DURATIONS = {1, 7, 30};

    public int mincostTickets(int[] days, int[] costs) {
        // memo[index] is the cheapest cover of days[index..], or -1 when unknown.
        int[] memo = new int[days.length];
        Arrays.fill(memo, -1);
        return cheapestFrom(0, days, costs, memo);
    }

    private int cheapestFrom(int index, int[] days, int[] costs, int[] memo) {
        if (index == days.length) {
            return 0;
        }
        if (memo[index] == -1) {
            int best = Integer.MAX_VALUE;
            for (int pass = 0; pass < DURATIONS.length; pass++) {
                int following = firstUncovered(index, DURATIONS[pass], days);
                best = Math.min(best, costs[pass] + cheapestFrom(following, days, costs, memo));
            }
            memo[index] = best;
        }
        return memo[index];
    }

    private int firstUncovered(int index, int duration, int[] days) {
        // A pass bought for days[index] covers through days[index] + duration - 1.
        int following = index;
        while (following < days.length && days[following] < days[index] + duration) {
            following++;
        }
        return following;
    }
}
