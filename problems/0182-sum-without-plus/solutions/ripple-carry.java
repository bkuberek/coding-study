public class Solution {
    private static final int WORD_BITS = 32;

    public int getSum(int a, int b) {
        int result = 0;
        int carry = 0;
        for (int position = 0; position < WORD_BITS; position++) {
            int x = (a >>> position) & 1;
            int y = (b >>> position) & 1;
            result |= (x ^ y ^ carry) << position;
            carry = (x & y) | (carry & (x ^ y)); // carry out: at least two of the three bits
        }
        return result;
    }
}
