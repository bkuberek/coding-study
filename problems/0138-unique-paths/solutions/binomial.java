import java.util.*;

public class Solution {
    private static final long MOD = 1_000_000_007L;

    public int uniquePaths(int m, int n) {
        // A route is a sequence of m + n - 2 moves; choose which of them are the shorter direction.
        long moves = m + n - 2;
        int chosen = Math.min(m, n) - 1;
        long numerator = 1;
        long denominator = 1;
        for (int step = 1; step <= chosen; step++) {
            numerator = numerator * (moves - chosen + step) % MOD;
            denominator = denominator * step % MOD;
        }
        // MOD is prime, so denominator^(MOD - 2) is its inverse (Fermat's little theorem).
        return (int) (numerator * power(denominator, MOD - 2) % MOD);
    }

    // Square-and-multiply; both factors stay below MOD, so each product fits in a long.
    private static long power(long base, long exponent) {
        long result = 1;
        long factor = base % MOD;
        for (long rest = exponent; rest > 0; rest >>= 1) {
            if ((rest & 1) == 1) {
                result = result * factor % MOD;
            }
            factor = factor * factor % MOD;
        }
        return result;
    }
}
