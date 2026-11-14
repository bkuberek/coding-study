public class Solution {
    public int[] countBits(int n) {
        int[] bits = new int[n + 1];
        for (int i = 1; i <= n; i++) {
            // i >> 1 drops the lowest bit of i and is smaller than i, so its count is known.
            bits[i] = bits[i >> 1] + (i & 1);
        }
        return bits;
    }
}
