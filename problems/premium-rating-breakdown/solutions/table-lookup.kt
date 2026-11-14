import java.math.BigDecimal
import java.math.RoundingMode

class Solution {
    fun ratePremium(
        classCode: String,
        payroll: BigDecimal,
        experienceMod: BigDecimal,
        scheduleCredit: BigDecimal,
        classCodes: Array<String>,
        baseRates: Array<BigDecimal>,
        bandLowerBounds: Array<BigDecimal>,
        bandFactors: Array<BigDecimal>,
        minimumPremium: BigDecimal,
    ): List<BigDecimal> {
        val rates = classCodes.zip(baseRates).toMap()
        val band = bandsAtOrBelow(bandLowerBounds, payroll) - 1
        val rate = rates[classCode]
        if (rate == null || band < 0) {
            return emptyList()
        }
        // BigDecimal / BigDecimal keeps the dividend's scale, so move the point instead.
        var running = payroll.movePointLeft(3) * rate
        val trail = mutableListOf(running)
        for (factor in listOf(bandFactors[band], experienceMod, BigDecimal.ONE - scheduleCredit)) {
            running *= factor
            trail.add(running)
        }
        trail.add(maxOf(running, minimumPremium).setScale(2, RoundingMode.HALF_UP))
        return trail
    }

    // Number of bands whose lower bound is <= payroll (upper bound of the sorted bounds).
    private fun bandsAtOrBelow(bounds: Array<BigDecimal>, payroll: BigDecimal): Int {
        var low = 0
        var high = bounds.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (bounds[middle] <= payroll) low = middle + 1 else high = middle
        }
        return low
    }
}
