class Solution {
    fun suggestedProducts(products: Array<String>, searchWord: String): List<List<String>> {
        val ordered = products.sorted()
        var start = 0
        return (1..searchWord.length).map { typed ->
            val prefix = searchWord.substring(0, typed)
            start = lowerBound(ordered, prefix, start)
            ordered.subList(start, minOf(start + 3, ordered.size)).filter { it.startsWith(prefix) }
        }
    }

    /** First index at or after [from] whose product is not smaller than [target]. */
    private fun lowerBound(ordered: List<String>, target: String, from: Int): Int {
        var low = from
        var high = ordered.size
        while (low < high) {
            val middle = (low + high) ushr 1
            if (ordered[middle] < target) low = middle + 1 else high = middle
        }
        return low
    }
}
