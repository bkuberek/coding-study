import java.math.BigDecimal;

public class Solution {
    public BigDecimal calculateTax(int[][] brackets, int income) {
        int cents = 0; // tax in hundredths of a unit: every rate is a whole percent
        int bracket = 0;
        for (int unit = 0; unit < income; unit++) {
            // Unit number unit covers income from unit to unit + 1.
            while (brackets[bracket][0] <= unit) {
                bracket++;
            }
            cents += brackets[bracket][1];
        }
        return BigDecimal.valueOf(cents, 2);
    }
}
