import java.math.BigDecimal;
import java.math.RoundingMode;

public class Solution {
    public BigDecimal bondPremium(BigDecimal contractPrice, BigDecimal[] bandFloors, BigDecimal[] ratesPerThousand) {
        BigDecimal total = BigDecimal.ZERO; // sum of slice * rate, exact
        for (int band = 0; band < bandFloors.length; band++) {
            BigDecimal lower = bandFloors[band];
            if (contractPrice.compareTo(lower) <= 0) {
                break;
            }
            BigDecimal upper = band + 1 < bandFloors.length ? bandFloors[band + 1] : contractPrice;
            BigDecimal slice = contractPrice.min(upper).subtract(lower);
            total = total.add(slice.multiply(ratesPerThousand[band]));
        }
        // Dividing by 1000 only moves the point, so it is exact; round once, at the end.
        return total.movePointLeft(3).setScale(2, RoundingMode.HALF_UP);
    }
}
