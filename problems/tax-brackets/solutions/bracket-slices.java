import java.math.BigDecimal;

public class Solution {
    public BigDecimal calculateTax(int[][] brackets, int income) {
        int cents = 0; // tax in hundredths of a unit: every rate is a whole percent
        int lower = 0;
        for (int[] bracket : brackets) {
            if (lower >= income) {
                break;
            }
            cents += (Math.min(bracket[0], income) - lower) * bracket[1];
            lower = bracket[0];
        }
        return BigDecimal.valueOf(cents, 2);
    }
}
