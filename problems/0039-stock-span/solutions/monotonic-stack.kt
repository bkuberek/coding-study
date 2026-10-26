class StockSpanner {
    private data class Entry(val price: Int, val span: Int)

    // Prices strictly decrease from bottom to top.
    private val stack = ArrayDeque<Entry>()

    fun span(price: Int): Int {
        var span = 1
        while (stack.isNotEmpty() && stack.last().price <= price) {
            span += stack.removeLast().span
        }
        stack.addLast(Entry(price, span))
        return span
    }
}
