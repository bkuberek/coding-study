public class Solution {
    public double myPow(double x, int n) {
        double base = n >= 0 ? x : 1 / x;
        long remaining = Math.abs((long) n); // Math.abs(Integer.MIN_VALUE) would stay negative
        double result = 1;
        long done = 0;
        while (done < remaining) {
            result *= base;
            done++;
            if (result == 1) {
                // base^done == 1, so the powers repeat with period done (x = 1 or x = -1).
                remaining = (remaining - done) % done;
                done = 0;
            } else if (result == 0 || Double.isInfinite(result)) {
                break; // further multiplications cannot change the result
            }
        }
        return result;
    }
}
