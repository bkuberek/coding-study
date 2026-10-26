class StockSpanner {
    private val prices = mutableListOf<Int>()

    fun span(price: Int): Int {
        prices.add(price)
        var day = prices.lastIndex
        while (day > 0 && prices[day - 1] <= price) {
            day--
        }
        return prices.size - day
    }
}
