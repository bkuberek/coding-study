// Debug: Running Total Overflow. Some tests fail: find the bug and fix it.
class Solution {
    fun invoiceTotal(unitPrices: IntArray, quantities: IntArray): Long =
        unitPrices.indices.sumOf { unitPrices[it] * quantities[it] }.toLong()
}
