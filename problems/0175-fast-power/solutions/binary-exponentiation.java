public class Solution {
    public double myPow(double x, int n) {
        // Widen first: -n overflows for n = Integer.MIN_VALUE.
        long exponent = n;
        if (exponent < 0) {
            x = 1 / x;
            exponent = -exponent;
        }
        double result = 1;
        // Invariant: result * x^exponent equals the original x^n.
        while (exponent > 0) {
            if ((exponent & 1) == 1) {
                result *= x;
            }
            x *= x;
            exponent >>= 1;
        }
        return result;
    }
}
