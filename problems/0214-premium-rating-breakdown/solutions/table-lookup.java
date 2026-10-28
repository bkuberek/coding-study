import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

public class Solution {
    public List<BigDecimal> ratePremium(
            String classCode,
            BigDecimal payroll,
            BigDecimal experienceMod,
            BigDecimal scheduleCredit,
            String[] classCodes,
            BigDecimal[] baseRates,
            BigDecimal[] bandLowerBounds,
            BigDecimal[] bandFactors,
            BigDecimal minimumPremium) {
        Map<String, BigDecimal> rates = new HashMap<>();
        for (int i = 0; i < classCodes.length; i++) {
            rates.put(classCodes[i], baseRates[i]);
        }
        int band = bandsAtOrBelow(bandLowerBounds, payroll) - 1;
        BigDecimal rate = rates.get(classCode);
        if (rate == null || band < 0) {
            return new ArrayList<>();
        }
        // Dividing by 1000 only moves the decimal point, so it stays exact.
        BigDecimal running = payroll.movePointLeft(3).multiply(rate);
        List<BigDecimal> trail = new ArrayList<>();
        trail.add(running);
        BigDecimal[] factors = {bandFactors[band], experienceMod, BigDecimal.ONE.subtract(scheduleCredit)};
        for (BigDecimal factor : factors) {
            running = running.multiply(factor);
            trail.add(running);
        }
        trail.add(running.max(minimumPremium).setScale(2, RoundingMode.HALF_UP));
        return trail;
    }

    // Number of bands whose lower bound is <= payroll (upper bound of the sorted bounds).
    private static int bandsAtOrBelow(BigDecimal[] bounds, BigDecimal payroll) {
        int low = 0;
        int high = bounds.length;
        while (low < high) {
            int middle = (low + high) >>> 1;
            if (bounds[middle].compareTo(payroll) <= 0) {
                low = middle + 1;
            } else {
                high = middle;
            }
        }
        return low;
    }
}
