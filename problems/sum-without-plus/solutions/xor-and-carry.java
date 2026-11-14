public class Solution {
    public int getSum(int a, int b) {
        // int is 32-bit two's complement, so the carry falls off the top bit as in hardware.
        while (b != 0) {
            int carry = (a & b) << 1;
            a ^= b; // the sum of every column, ignoring carries
            b = carry;
        }
        return a;
    }
}
