// Debug: Running Total Overflow. Some tests fail: find the bug and fix it.
public class Solution {
    public long invoiceTotal(int[] unitPrices, int[] quantities) {
        int total = 0;
        for (int i = 0; i < unitPrices.length; i++) {
            total += unitPrices[i] * quantities[i];
        }
        return (long) total;
    }
}
