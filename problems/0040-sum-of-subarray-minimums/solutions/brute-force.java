import java.util.*;

public class Solution {
    private static final int MOD = 1_000_000_007;

    public int sumSubarrayMins(int[] arr) {
        long total = 0;
        for (int start = 0; start < arr.length; start++) {
            int minimum = arr[start];
            for (int end = start; end < arr.length; end++) {
                minimum = Math.min(minimum, arr[end]);
                total += minimum;
            }
            total %= MOD;
        }
        return (int) total;
    }
}
