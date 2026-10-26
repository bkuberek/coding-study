public class Solution {
    public long invoiceTotal(int[] unitPrices, int[] quantities) {
        long total = 0;
        for (int i = 0; i < unitPrices.length; i++) {
            total += (long) unitPrices[i] * quantities[i];
        }
        return total;
    }
}
