import java.math.BigDecimal
import java.math.RoundingMode

class Solution {
    fun bondPremium(contractPrice: BigDecimal, bandFloors: Array<BigDecimal>, ratesPerThousand: Array<BigDecimal>): BigDecimal {
        var total = BigDecimal.ZERO // sum of slice * rate, exact
        for (band in bandFloors.indices) {
            val lower = bandFloors[band]
            if (contractPrice <= lower) break
            val upper = if (band + 1 < bandFloors.size) bandFloors[band + 1] else contractPrice
            total += (minOf(contractPrice, upper) - lower) * ratesPerThousand[band]
        }
        // `/ 1000` would keep the total's scale and round half-even; move the point and round once instead.
        return total.movePointLeft(3).setScale(2, RoundingMode.HALF_UP)
    }
}
