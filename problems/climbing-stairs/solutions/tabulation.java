import java.util.*;

public class Solution {
    public int climbStairs(int n) {
        // ways[step] counts the move sequences that end exactly on `step`.
        int[] ways = new int[n + 1];
        ways[0] = 1;
        ways[1] = 1;
        for (int step = 2; step <= n; step++) {
            ways[step] = ways[step - 1] + ways[step - 2];
        }
        return ways[n];
    }
}
