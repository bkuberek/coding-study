import java.util.*;

public class Solution {
    private static final int MOD = 1_000_000_007;

    public int sumSubarrayMins(int[] arr) {
        // ending[i] is the sum of the minimums of the subarrays that end at i (at most 9 * 10^8).
        long[] ending = new long[arr.length];
        // Indexes whose values strictly increase from bottom to top: stack[0 .. size).
        int[] stack = new int[arr.length];
        int size = 0;
        long total = 0;
        for (int index = 0; index < arr.length; index++) {
            int value = arr[index];
            while (size > 0 && arr[stack[size - 1]] >= value) {
                size--;
            }
            if (size > 0) {
                int previous = stack[size - 1];
                // Starts after the previous smaller element have minimum `value`; earlier starts
                // have the same minimums as the subarrays ending at `previous`.
                ending[index] = ending[previous] + (long) value * (index - previous);
            } else {
                ending[index] = (long) value * (index + 1);
            }
            stack[size++] = index;
            total = (total + ending[index]) % MOD;
        }
        return (int) total;
    }
}
