class Solution {
    fun invoiceTotal(unitPrices: IntArray, quantities: IntArray): Long =
        unitPrices.indices.sumOf { unitPrices[it].toLong() * quantities[it] }
}
