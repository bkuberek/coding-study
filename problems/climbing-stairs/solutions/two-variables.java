import java.util.*;

public class Solution {
    public int climbStairs(int n) {
        // Before each iteration: twoBelow and oneBelow count the ways to reach the two steps
        // just below the one being computed.
        int twoBelow = 1;
        int oneBelow = 1;
        for (int step = 2; step <= n; step++) {
            int current = oneBelow + twoBelow;
            twoBelow = oneBelow;
            oneBelow = current;
        }
        return oneBelow;
    }
}
