class Solution {
    fun rankPlayers(names: Array<String>, scores: IntArray): Array<String> {
        val order = names.indices.sortedWith(
            compareByDescending<Int> { scores[it] }.thenBy { names[it] },
        )
        return Array(order.size) { names[order[it]] }
    }
}
