import java.util.*;

public class Solution {
    private static final int MOD = 1_000_000_007;

    public int sumSubarrayMins(int[] arr) {
        long total = 0;
        // Indexes whose values strictly increase from bottom to top: stack[0 .. size).
        int[] stack = new int[arr.length + 1];
        int size = 0;
        // One extra step with value 0, below every element, pops whatever is left.
        for (int index = 0; index <= arr.length; index++) {
            int value = index < arr.length ? arr[index] : 0;
            while (size > 0 && arr[stack[size - 1]] >= value) {
                int middle = stack[--size];
                // Starts after the previous strictly smaller element, ends before the next
                // smaller-or-equal one (index): arr[middle] is the minimum of left * right subarrays.
                long left = middle - (size > 0 ? stack[size - 1] : -1);
                long right = index - middle;
                total = (total + arr[middle] * left * right) % MOD;
            }
            stack[size++] = index;
        }
        return (int) total;
    }
}
