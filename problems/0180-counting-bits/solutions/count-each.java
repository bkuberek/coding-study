public class Solution {
    public int[] countBits(int n) {
        int[] bits = new int[n + 1];
        for (int i = 0; i <= n; i++) {
            int count = 0;
            for (int word = i; word != 0; word &= word - 1) {
                count++; // each step clears the lowest set bit
            }
            bits[i] = count;
        }
        return bits;
    }
}
