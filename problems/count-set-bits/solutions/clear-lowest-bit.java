public class Solution {
    public int hammingWeight(long n) {
        // The low 32 bits as an int: values from 2^31 up become negative, with the same bits.
        int word = (int) n;
        int count = 0;
        while (word != 0) {
            word &= word - 1; // clears the lowest set bit
            count++;
        }
        return count;
    }
}
