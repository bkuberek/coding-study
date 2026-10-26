import java.util.*;

public class Solution {
    public int climbStairs(int n) {
        // memo[step] is 0 until the count for `step` has been computed.
        return ways(n, new int[n + 1]);
    }

    private int ways(int step, int[] memo) {
        if (step <= 1) {
            return 1;
        }
        if (memo[step] == 0) {
            memo[step] = ways(step - 1, memo) + ways(step - 2, memo);
        }
        return memo[step];
    }
}
