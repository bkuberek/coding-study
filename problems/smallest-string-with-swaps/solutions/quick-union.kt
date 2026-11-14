class Solution {
    fun smallestStringWithSwaps(s: String, pairs: Array<IntArray>): String {
        val parent = IntArray(s.length) { it } // parent[x] == x marks a root

        fun find(start: Int): Int {
            var x = start
            while (parent[x] != x) x = parent[x]
            return x
        }

        for ((a, b) in pairs) {
            val rootA = find(a)
            val rootB = find(b)
            if (rootA != rootB) parent[rootA] = rootB // no balancing: trees can grow into long chains
        }
        val letters = s.toCharArray()
        // groupBy keeps the positions of each group in increasing order.
        for (positions in s.indices.groupBy(::find).values) {
            positions.zip(positions.map { s[it] }.sorted()).forEach { (position, letter) -> letters[position] = letter }
        }
        return String(letters)
    }
}
