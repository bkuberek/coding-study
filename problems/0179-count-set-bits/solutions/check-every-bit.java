public class Solution {
    private static final int WORD_BITS = 32;

    public int hammingWeight(long n) {
        int count = 0;
        for (int position = 0; position < WORD_BITS; position++) {
            count += (int) ((n >>> position) & 1L);
        }
        return count;
    }
}
